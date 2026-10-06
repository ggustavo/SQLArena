import json
import logging
from typing import Optional, Tuple, Dict, Any, List
import redis
from app.config import settings

logger = logging.getLogger("RedisClient")

class RedisClient:
    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.REDIS_URL
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.url, decode_responses=True)
        return self._client

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except Exception as e:
            logger.warning(f"Erro ao conectar ao Redis: {e}")
            return False

    def check_rate_limit(self, user_id: str, limit_seconds: int = 5) -> Tuple[bool, int]:
        """
        Verifica se o usuário respeitou o intervalo de submissão (Rate Limit de 5 segundos).
        Retorna (permitido: bool, tempo_restante_segundos: int).
        """
        key = f"ratelimit:{user_id}"
        try:
            # Tenta definir a chave apenas se ela NÃO existir (NX) com expiração (EX)
            acquired = self.client.set(key, "active", ex=limit_seconds, nx=True)
            if acquired:
                return True, 0
            
            # Se a chave já existe, obtém o TTL restante
            ttl = self.client.ttl(key)
            return False, max(1, ttl if ttl > 0 else limit_seconds)
        except Exception as e:
            logger.error(f"Erro no rate limit Redis: {e}")
            # Em caso de falha no Redis, permite a execução para não bloquear o usuário
            return True, 0

    def set_answer_hash(self, question_id: int, answer_hash: str) -> bool:
        """Armazena o Hash SHA-256 canônico oficial do gabarito."""
        key = f"question:{question_id}:answer_hash"
        try:
            self.client.set(key, answer_hash)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar hash no Redis: {e}")
            return False

    def get_answer_hash(self, question_id: int) -> Optional[str]:
        """Recupera o Hash SHA-256 canônico do gabarito."""
        key = f"question:{question_id}:answer_hash"
        try:
            return self.client.get(key)
        except Exception as e:
            logger.error(f"Erro ao ler hash do Redis: {e}")
            return None

    def set_submission_status(self, submission_id: str, data: Dict[str, Any], ttl: int = 7200) -> bool:
        """Armazena o status da submissão para resposta instantânea ao polling do frontend."""
        key = f"submission:{submission_id}:status"
        try:
            self.client.set(key, json.dumps(data), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar status da submissão no Redis: {e}")
            return False

    def get_submission_status(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Recupera o status atual da submissão para polling."""
        key = f"submission:{submission_id}:status"
        try:
            val = self.client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.error(f"Erro ao ler status da submissão do Redis: {e}")
            return None

    def delete_submission(self, submission_id: str) -> bool:
        """Remove o cache de status de uma submissão."""
        key = f"submission:{submission_id}:status"
        try:
            self.client.delete(key)
            return True
        except Exception:
            return False

    def set_cached_questions(self, role: str, data: List[Dict[str, Any]], ttl: int = 300) -> bool:
        """Armazena a lista de questões no cache Redis (TTL 300s)."""
        key = f"questions:list:{role.lower()}"
        try:
            self.client.set(key, json.dumps(data), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar cache de questões no Redis: {e}")
            return False

    def get_cached_questions(self, role: str) -> Optional[List[Dict[str, Any]]]:
        """Recupera a lista de questões em cache no Redis."""
        key = f"questions:list:{role.lower()}"
        try:
            val = self.client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.error(f"Erro ao ler cache de questões do Redis: {e}")
            return None

    def set_cached_question(self, question_id: int, data: Dict[str, Any], ttl: int = 300) -> bool:
        """Armazena os detalhes de uma questão no cache Redis (TTL 300s)."""
        key = f"question:{question_id}:details"
        try:
            self.client.set(key, json.dumps(data), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar cache da questão #{question_id} no Redis: {e}")
            return False

    def get_cached_question(self, question_id: int) -> Optional[Dict[str, Any]]:
        """Recupera os detalhes de uma questão em cache no Redis."""
        key = f"question:{question_id}:details"
        try:
            val = self.client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.error(f"Erro ao ler cache da questão #{question_id} do Redis: {e}")
            return None

    def invalidate_questions_cache(self, question_id: Optional[int] = None) -> bool:
        """Invalida os caches de lista e específicos de questões no Redis."""
        try:
            keys_to_delete = ["questions:list:student", "questions:list:instructor", "questions:list:admin"]
            if question_id is not None:
                keys_to_delete.append(f"question:{question_id}:details")
                keys_to_delete.append(f"question:{question_id}:answer_hash")
            self.client.delete(*keys_to_delete)
            logger.info(f"[Redis] Cache de questões invalidado com sucesso. Chaves: {keys_to_delete}")
            return True
        except Exception as e:
            logger.error(f"Erro ao invalidar cache de questões no Redis: {e}")
            return False

redis_client = RedisClient()
