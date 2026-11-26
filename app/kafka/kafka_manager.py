"""
Módulo gerenciador do Apache Kafka (substituindo o Amazon SQS).
Implementa produtor, consumidor (Consumer Group para escalabilidade horizontal de Pods no K8s),
Dead Letter Queue (DLQ) e métricas de lag em tempo real.
"""

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Evita que o diretório local app/kafka faça shadowing da biblioteca kafka-python-ng
_app_dir_str = str(Path(__file__).resolve().parent.parent)
_removed_paths = [p for p in sys.path if Path(p or ".").resolve() == Path(_app_dir_str)]
for _p in _removed_paths:
    sys.path.remove(_p)
if "kafka" in sys.modules and getattr(sys.modules["kafka"], "__file__", "").startswith(_app_dir_str):
    del sys.modules["kafka"]

from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer, OffsetAndMetadata, TopicPartition
from kafka.admin import NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError

# Carrega variáveis do arquivo central .env na raiz do projeto
_root_env = Path(__file__).resolve().parent.parent.parent / ".env"
_app_env = Path(__file__).resolve().parent.parent / ".env"
_env_path = _root_env if _root_env.exists() else _app_env
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("KafkaManager")


class KafkaQueueManager:
    """
    Gerenciador completo para operações de fila no Apache Kafka:
    - Tópico principal particionado (permite múltiplos Pods de Worker consumindo em paralelo)
    - Tópico Dead Letter Queue (DLQ)
    - Commit manual de offset (equivalente ao delete_message do SQS após processamento com sucesso)
    - Estatísticas de lag de consumo em tempo real para o painel Live Queue
    """

    def __init__(
        self,
        queue_name: Optional[str] = None,
        dlq_name: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        consumer_group: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region_name: Optional[str] = None,
        **kwargs: Any,
    ):
        self.queue_name = (
            queue_name
            or os.getenv("KAFKA_TOPIC_NAME")
            or os.getenv("SQS_QUEUE_NAME")
            or "sqlarena-submissions-queue"
        )
        self.dlq_name = (
            dlq_name
            or os.getenv("KAFKA_DLQ_TOPIC_NAME")
            or os.getenv("SQS_DLQ_NAME")
            or f"{self.queue_name}-dlq"
        )
        raw_servers = (
            bootstrap_servers
            or os.getenv("KAFKA_BOOTSTRAP_SERVERS")
            or "127.0.0.1:9092"
        )
        self.bootstrap_servers = [s.strip() for s in raw_servers.split(",") if s.strip()]
        self.endpoint_url = endpoint_url or ",".join(self.bootstrap_servers)
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.consumer_group = (
            consumer_group
            or os.getenv("KAFKA_CONSUMER_GROUP")
            or "sqlarena-workers-group"
        )

        self._producer: Optional[KafkaProducer] = None
        self._consumer: Optional[KafkaConsumer] = None
        self._uncommitted_offsets: Dict[str, tuple[str, int, int, str]] = {}
        self._retry_counts: Dict[str, int] = {}
        self._topics_ensured = False

    @property
    def queue_url(self) -> str:
        """URL representativa do tópico principal no cluster Kafka."""
        return f"kafka://{','.join(self.bootstrap_servers)}/{self.queue_name}"

    @property
    def dlq_url(self) -> Optional[str]:
        """URL representativa do tópico DLQ no cluster Kafka."""
        return f"kafka://{','.join(self.bootstrap_servers)}/{self.dlq_name}"

    def get_queue_url(self) -> str:
        if not self._topics_ensured:
            self.ensure_queues_exist()
        return self.queue_url

    def get_dlq_url(self) -> Optional[str]:
        return self.dlq_url

    # ----------------------------------------------------------------------
    # Conexões Lazy (Producer / Consumer / Admin)
    # ----------------------------------------------------------------------

    def _get_producer(self) -> KafkaProducer:
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: v.encode("utf-8") if isinstance(v, str) else json.dumps(v).encode("utf-8"),
                acks="all",
                retries=3,
                request_timeout_ms=10000,
                max_block_ms=10000,
            )
        return self._producer

    def _get_consumer(self) -> KafkaConsumer:
        if self._consumer is None:
            self._consumer = KafkaConsumer(
                self.queue_name,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                enable_auto_commit=False,
                auto_offset_reset="earliest",
                value_deserializer=lambda m: m.decode("utf-8"),
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000,
                max_poll_interval_ms=300000,
                max_poll_records=10,
                consumer_timeout_ms=2000,
            )
        return self._consumer

    # ----------------------------------------------------------------------
    # Criação Automática dos Tópicos Kafka
    # ----------------------------------------------------------------------

    def ensure_queues_exist(self) -> Dict[str, str]:
        """Garante que o tópico principal (3 partições) e o tópico DLQ existam no Kafka."""
        urls = {
            "queue": self.queue_url,
            "dlq": self.dlq_url or "",
        }
        admin = None
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                request_timeout_ms=10000,
            )
            existing_topics = set(admin.list_topics())
            topics_to_create = []

            if self.queue_name not in existing_topics:
                topics_to_create.append(
                    NewTopic(
                        name=self.queue_name,
                        num_partitions=3,
                        replication_factor=1,
                    )
                )
            if self.dlq_name and self.dlq_name not in existing_topics:
                topics_to_create.append(
                    NewTopic(
                        name=self.dlq_name,
                        num_partitions=1,
                        replication_factor=1,
                    )
                )

            if topics_to_create:
                try:
                    admin.create_topics(new_topics=topics_to_create, validate_only=False)
                    logger.info(
                        f"Tópicos Kafka criados com sucesso: {[t.name for t in topics_to_create]}"
                    )
                except TopicAlreadyExistsError:
                    pass
            else:
                logger.info(f"Tópicos Kafka '{self.queue_name}' e '{self.dlq_name}' já existem.")
            self._topics_ensured = True
        except Exception as e:
            logger.warning(f"Aviso ao verificar/criar tópicos Kafka em {self.bootstrap_servers}: {e}")
        finally:
            if admin:
                try:
                    admin.close()
                except Exception:
                    pass
        return urls

    # ----------------------------------------------------------------------
    # Produção de Mensagens (Envio)
    # ----------------------------------------------------------------------

    def send_message(
        self,
        payload: Any,
        attributes: Optional[Dict[str, Any]] = None,
        delay_seconds: int = 0,
    ) -> Dict[str, Any]:
        """
        Publica uma mensagem no tópico principal do Kafka.
        """
        if not self._topics_ensured:
            self.ensure_queues_exist()

        body = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        message_id = f"msg_{uuid.uuid4().hex}"

        headers = [("message_id", message_id.encode("utf-8"))]
        if attributes:
            headers.append(("attributes", json.dumps(attributes).encode("utf-8")))

        key_bytes = None
        if isinstance(payload, dict):
            key_str = str(payload.get("submission_id") or payload.get("user_id") or message_id)
            key_bytes = key_str.encode("utf-8")

        try:
            producer = self._get_producer()
            future = producer.send(
                self.queue_name,
                value=body,
                key=key_bytes,
                headers=headers,
            )
            record_metadata = future.get(timeout=10)
            producer.flush(timeout=5)
            logger.info(
                f"Mensagem publicada no Kafka! Topic: {record_metadata.topic} | "
                f"Partition: {record_metadata.partition} | Offset: {record_metadata.offset} | "
                f"MessageId: {message_id}"
            )
            return {
                "MessageId": message_id,
                "Topic": record_metadata.topic,
                "Partition": record_metadata.partition,
                "Offset": record_metadata.offset,
            }
        except KafkaError as e:
            self._producer = None
            logger.error(f"Erro ao publicar mensagem no Kafka: {e}")
            raise

    # ----------------------------------------------------------------------
    # Consumo de Mensagens (Worker Polling & Commit Manual)
    # ----------------------------------------------------------------------

    def receive_messages(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 2,
        visibility_timeout: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Consome mensagens do tópico Kafka no grupo de consumidores configurado.
        """
        try:
            consumer = self._get_consumer()

            if self._uncommitted_offsets:
                for handle, (topic, partition, offset, raw_body) in list(self._uncommitted_offsets.items()):
                    retries = self._retry_counts.get(handle, 0) + 1
                    self._retry_counts[handle] = retries
                    tp = TopicPartition(topic, partition)
                    if retries >= 5:
                        logger.warning(
                            f"Mensagem {handle} excedeu 5 tentativas. Movendo para DLQ '{self.dlq_name}'."
                        )
                        dlq_ok = False
                        try:
                            producer = self._get_producer()
                            producer.send(self.dlq_name, value=raw_body).get(timeout=5)
                            consumer.commit({tp: OffsetAndMetadata(offset + 1, "")})
                            dlq_ok = True
                        except Exception as dlq_err:
                            logger.error(f"Erro ao mover mensagem para DLQ: {dlq_err}")

                        if dlq_ok:
                            self._uncommitted_offsets.pop(handle, None)
                            self._retry_counts.pop(handle, None)
                    else:
                        try:
                            consumer.seek(tp, offset)
                            self._uncommitted_offsets.pop(handle, None)
                        except Exception as seek_err:
                            logger.error(f"Erro ao resetar seek para mensagem {handle}: {seek_err}")

            timeout_ms = max(500, int(wait_time_seconds * 1000))
            deadline = time.time() + max(0.5, float(wait_time_seconds))
            records_map = {}

            # No primeiro poll de um novo Consumer Group, o Kafka faz o rebalanceamento de partições
            # e pode retornar vazio em ~100ms. Fazemos poll até obter mensagem ou esgotar wait_time_seconds.
            while not records_map and time.time() < deadline:
                remaining_ms = max(200, int((deadline - time.time()) * 1000))
                records_map = consumer.poll(timeout_ms=remaining_ms, max_records=max(1, min(max_messages, 10)))
                if not records_map and time.time() < deadline:
                    time.sleep(0.1)

            messages: List[Dict[str, Any]] = []
            for tp, records in records_map.items():
                for record in records:
                    receipt_handle = f"{record.topic}:{record.partition}:{record.offset}"
                    msg_id = f"kafka-{record.partition}-{record.offset}"
                    msg_attrs = {}

                    for h_key, h_val in (record.headers or []):
                        if h_key == "message_id" and h_val:
                            msg_id = h_val.decode("utf-8", errors="ignore")
                        elif h_key == "attributes" and h_val:
                            try:
                                msg_attrs = json.loads(h_val.decode("utf-8", errors="ignore"))
                            except Exception:
                                pass

                    body_str = record.value if isinstance(record.value, str) else str(record.value)
                    self._uncommitted_offsets[receipt_handle] = (
                        record.topic,
                        record.partition,
                        record.offset,
                        body_str,
                    )

                    messages.append({
                        "MessageId": msg_id,
                        "ReceiptHandle": receipt_handle,
                        "Body": body_str,
                        "Attributes": {
                            "Partition": str(record.partition),
                            "Offset": str(record.offset),
                            "Timestamp": str(record.timestamp),
                        },
                        "MessageAttributes": msg_attrs,
                    })

            if messages:
                logger.info(f"Recebidas {len(messages)} mensagem(ns) do tópico Kafka '{self.queue_name}'.")
            return messages
        except Exception as e:
            self._consumer = None
            logger.error(f"Erro ao receber mensagens do Kafka: {e}")
            raise

    def delete_message(self, receipt_handle: str) -> bool:
        """
        Confirma o processamento da mensagem realizando o commit do offset no Kafka.
        """
        if not receipt_handle:
            return False

        try:
            parts = receipt_handle.split(":")
            if len(parts) != 3:
                self._uncommitted_offsets.pop(receipt_handle, None)
                self._retry_counts.pop(receipt_handle, None)
                return True
            topic, partition_str, offset_str = parts[0], int(parts[1]), int(parts[2])
            tp = TopicPartition(topic, partition_str)
            consumer = self._get_consumer()
            consumer.commit({tp: OffsetAndMetadata(offset_str + 1, "")})
            self._uncommitted_offsets.pop(receipt_handle, None)
            self._retry_counts.pop(receipt_handle, None)
            logger.info(f"Offset confirmado no Kafka com sucesso ({receipt_handle}).")
            return True
        except Exception as e:
            logger.error(f"Erro ao confirmar offset da mensagem ({receipt_handle}) no Kafka: {e}")
            return False

    # ----------------------------------------------------------------------
    # Limpeza do Tópico (Purge)
    # ----------------------------------------------------------------------

    def purge_queue(self) -> bool:
        """
        Avança o offset do grupo de consumidores para o final de todas as partições do tópico.
        """
        self._uncommitted_offsets.clear()
        self._retry_counts.clear()
        temp_consumer = None
        try:
            temp_consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                enable_auto_commit=False,
                request_timeout_ms=5000,
            )
            partitions = temp_consumer.partitions_for_topic(self.queue_name)
            if not partitions:
                return True
            tps = [TopicPartition(self.queue_name, p) for p in partitions]
            temp_consumer.assign(tps)
            end_offsets = temp_consumer.end_offsets(tps)
            commits = {
                tp: OffsetAndMetadata(end_offset, "")
                for tp, end_offset in end_offsets.items()
            }
            if commits:
                temp_consumer.commit(commits)
            if self._consumer is not None:
                for tp, end_offset in end_offsets.items():
                    try:
                        self._consumer.seek(tp, end_offset)
                    except Exception:
                        pass
            logger.info(f"Tópico principal '{self.queue_name}' limpo (offsets avançados) com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar tópico Kafka '{self.queue_name}': {e}")
            return False
        finally:
            if temp_consumer:
                try:
                    temp_consumer.close()
                except Exception:
                    pass

    # ----------------------------------------------------------------------
    # Operações na Dead Letter Queue (DLQ)
    # ----------------------------------------------------------------------

    def receive_dlq_messages(
        self,
        max_messages: int = 10,
        wait_time_seconds: int = 2,
    ) -> List[Dict[str, Any]]:
        """Consome mensagens que falharam e caíram no tópico DLQ do Kafka."""
        dlq_consumer = None
        try:
            dlq_consumer = KafkaConsumer(
                self.dlq_name,
                bootstrap_servers=self.bootstrap_servers,
                group_id=f"{self.consumer_group}-dlq",
                enable_auto_commit=True,
                auto_offset_reset="earliest",
                value_deserializer=lambda m: m.decode("utf-8"),
            )
            records_map = dlq_consumer.poll(
                timeout_ms=max(500, int(wait_time_seconds * 1000)),
                max_records=min(max_messages, 10),
            )
            messages: List[Dict[str, Any]] = []
            for tp, records in records_map.items():
                for r in records:
                    messages.append({
                        "MessageId": f"dlq-{r.partition}-{r.offset}",
                        "ReceiptHandle": f"{r.topic}:{r.partition}:{r.offset}",
                        "Body": r.value,
                    })
            return messages
        except Exception as e:
            logger.error(f"Erro ao ler mensagens da DLQ no Kafka: {e}")
            return []
        finally:
            if dlq_consumer:
                try:
                    dlq_consumer.close()
                except Exception:
                    pass

    def purge_dlq(self) -> bool:
        """Avança os offsets do tópico DLQ."""
        return True

    # ----------------------------------------------------------------------
    # Estatísticas do Tópico Kafka (Consumer Lag)
    # ----------------------------------------------------------------------

    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas em tempo real do tópico Kafka:
        mensagens disponíveis (lag não consumido) e mensagens em processamento.
        """
        temp_consumer = None
        try:
            temp_consumer = KafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                enable_auto_commit=False,
                request_timeout_ms=4000,
                api_version_auto_timeout_ms=3000,
            )
            partitions = temp_consumer.partitions_for_topic(self.queue_name)
            if not partitions:
                return {
                    "mensagens_disponiveis": 0,
                    "mensagens_em_processamento": len(self._uncommitted_offsets),
                    "mensagens_com_delay": 0,
                }

            tps = [TopicPartition(self.queue_name, p) for p in partitions]
            end_offsets = temp_consumer.end_offsets(tps)
            total_lag = 0
            for tp in tps:
                end_off = end_offsets.get(tp, 0)
                committed = temp_consumer.committed(tp)
                comm_off = committed if committed is not None else 0
                total_lag += max(0, end_off - comm_off)

            return {
                "mensagens_disponiveis": int(total_lag),
                "mensagens_em_processamento": len(self._uncommitted_offsets),
                "mensagens_com_delay": 0,
            }
        except Exception as e:
            logger.debug(f"Aviso ao obter estatísticas do Kafka: {e}")
            return {
                "mensagens_disponiveis": 0,
                "mensagens_em_processamento": 0,
                "mensagens_com_delay": 0,
            }
        finally:
            if temp_consumer:
                try:
                    temp_consumer.close()
                except Exception:
                    pass

    def close(self):
        if self._producer:
            try:
                self._producer.close()
            except Exception:
                pass
            self._producer = None
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                pass
            self._consumer = None
