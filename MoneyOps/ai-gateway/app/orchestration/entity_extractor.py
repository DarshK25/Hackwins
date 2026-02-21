"""
Entity extractor: regex first, LLM second, then aggregated response
"""
from typing import Dict, Any, List, Optional
import time
import re
from decimal import Decimal

from app.llm.groq_client import groq_client
from app.utils.logger import get_logger
from app.schemas.entities import (
    Entity,
    EntityType,
    ExtractedEntities,
    normalize_amount,
    normalize_time_period,
    normalize_metric,
    ENTITY_PATTERNS,
)
from app.schemas.intents import Intent

logger = get_logger(__name__)


class EntityExtractor:
    """Extracts entities from user input using regex + LLM. Supports operational & strategic intents.

    Args:
        use_llm_for_operational: force LLM calls even for simple intents (default False)
        max_llm_entities: maximum entities taken from LLM output to avoid overload
    """

    def __init__(self, use_llm_for_operational: bool = False, max_llm_entities: int = 25):
        self.groq = groq_client
        self.use_llm_for_operational = use_llm_for_operational
        self.max_llm_entities = max_llm_entities
        # cache compiled regex patterns for performance
        self._compiled_patterns: Dict[EntityType, List[re.Pattern]] = {
            k: [re.compile(p, re.IGNORECASE) for p in v]
            for k, v in ENTITY_PATTERNS.items()
        }

    async def extract(
        self,
        user_input: str,
        intent: Intent,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExtractedEntities:
        start_time = time.time()
        entities: List[Entity] = []

        # 1) regex extraction (fast)
        try:
            regex_entities = self._regex_extract(user_input)
            entities.extend(regex_entities)
        except Exception as e:
            logger.warning("regex_extract_failed", error=str(e))

        # 2) LLM extraction for complex entities or when regex found nothing
        from app.schemas.intents import get_intent_requirements, ComplexityLevel

        requirements = get_intent_requirements(intent)
        call_llm = (
            self.use_llm_for_operational
            or requirements.complexity in {ComplexityLevel.COMPLEX, ComplexityLevel.STRATEGIC}
            or len(entities) == 0
        )

        if call_llm:
            try:
                llm_entities = await self._llm_extract(user_input, intent, context)
                if self.max_llm_entities and len(llm_entities) > self.max_llm_entities:
                    logger.debug("llm_entities_truncated", returned=len(llm_entities), max=self.max_llm_entities)
                    llm_entities = llm_entities[: self.max_llm_entities]
                entities.extend(llm_entities)
            except Exception as e:
                logger.warning("llm_extract_failed", error=str(e))

        result = self._build_response(entities, user_input)
        result.confidence_score = float(result.confidence_score)
        elapsed = int((time.time() - start_time) * 1000)
        logger.debug("entity_extraction_completed", total_entities=result.total_entities, time_ms=elapsed)
        return result

    def _regex_extract(self, user_input: str) -> List[Entity]:
        entities: List[Entity] = []
        text = user_input or ""

        # Amounts
        for pattern in self._compiled_patterns.get(EntityType.AMOUNT, []):
            for m in pattern.finditer(text):
                raw = m.group(0)
                try:
                    normalized = normalize_amount(raw)
                    entities.append(Entity(
                        entity_type=EntityType.AMOUNT,
                        value=raw,
                        raw_text=raw,
                        confidence=0.95,
                        normalized_value=normalized,
                        extraction_method="regex",
                    ))
                except Exception:
                    continue

        # Phone
        for pattern in self._compiled_patterns.get(EntityType.PHONE, []):
            for m in pattern.finditer(text):
                val = m.group(0)
                entities.append(Entity(
                    entity_type=EntityType.PHONE,
                    value=val,
                    raw_text=val,
                    confidence=0.95,
                    extraction_method="regex",
                ))

        # Email
        for pattern in self._compiled_patterns.get(EntityType.EMAIL, []):
            for m in pattern.finditer(text):
                val = m.group(0)
                entities.append(Entity(
                    entity_type=EntityType.EMAIL,
                    value=val,
                    raw_text=val,
                    confidence=0.95,
                    extraction_method="regex",
                ))

        # GST
        for pattern in self._compiled_patterns.get(EntityType.GST_NUMBER, []):
            for m in pattern.finditer(text):
                val = m.group(0)
                entities.append(Entity(
                    entity_type=EntityType.GST_NUMBER,
                    value=val,
                    raw_text=val,
                    confidence=0.95,
                    extraction_method="regex",
                ))

        # Percentage
        for pattern in self._compiled_patterns.get(EntityType.PERCENTAGE, []):
            for m in pattern.finditer(text):
                val = m.group(0)
                entities.append(Entity(
                    entity_type=EntityType.PERCENTAGE,
                    value=val,
                    raw_text=val,
                    confidence=0.9,
                    extraction_method="regex",
                ))

        return entities

    async def _llm_extract(self, user_input: str, intent: Intent, context: Optional[Dict[str, Any]]) -> List[Entity]:
        """Run Groq and parse returned entities. Uses chat_completion_with_json for structured response."""
        prompt = self._build_extraction_prompt(user_input, intent, context)

        messages = [{"role": "user", "content": prompt}]

        # Use the helper that returns parsed JSON if possible
        response = await self.groq.chat_completion_with_json(messages=messages, temperature=0.0, max_tokens=800)

        return self._parse_llm_entities(response)

    def _build_extraction_prompt(self, user_input: str, intent: Intent, context: Optional[Dict[str, Any]]) -> str:
        prompt = f"""You are an entity extractor for MoneyOps. Extract explicit entities from the user input.

User Input: "{user_input}"
Intent: {intent.name}

Return ONLY a JSON array of entities like:
[
  {"type": "client_name", "value": "Acme Corp", "confidence": 0.95},
  {"type": "amount", "value": "50000", "confidence": 0.9}
]

Important:
- Return [] if none found
- Confidence 0.0 - 1.0
- Use snake_case keys for types
- Extract only explicitly mentioned values (do not fabricate)
"""

        if context:
            prompt += f"\nContext: {context}\n"

        return prompt

    def _parse_llm_entities(self, response: Any) -> List[Entity]:
        import json

        entities: List[Entity] = []

        try:
            # Groq client may already return a dict/list
            if isinstance(response, (list, tuple)):
                data = response
            elif isinstance(response, dict):
                # commonly the JSON will be the dict itself or contain 'entities'
                if "entities" in response and isinstance(response["entities"], list):
                    data = response["entities"]
                else:
                    # try to find the first list value
                    lists = [v for v in response.values() if isinstance(v, list)]
                    data = lists[0] if lists else []
            else:
                # fallback to extracting JSON substring
                s = str(response)
                start = s.find("[")
                end = s.rfind("]") + 1
                if start == -1 or end == 0:
                    return []
                data = json.loads(s[start:end])

            for item in data:
                typ = item.get("type")
                if not typ:
                    continue
                type_key = typ.strip().upper()
                # map basic known keys
                mapping = {
                    "CLIENT_NAME": EntityType.CLIENT_NAME,
                    "CLIENT": EntityType.CLIENT_NAME,
                    "INVOICE_ID": EntityType.INVOICE_ID,
                    "AMOUNT": EntityType.AMOUNT,
                    "PHONE": EntityType.PHONE,
                    "EMAIL": EntityType.EMAIL,
                    "GST_NUMBER": EntityType.GST_NUMBER,
                    "PERCENTAGE": EntityType.PERCENTAGE,
                    "PROBLEM_AREA": EntityType.PROBLEM_AREA,
                    "TIME_PERIOD": EntityType.TIME_PERIOD,
                    "TARGET_VALUE": EntityType.TARGET_VALUE,
                    "TARGET_METRIC": EntityType.METRIC,
                    "METRIC": EntityType.METRIC,
                    "COMPETITOR": EntityType.COMPETITOR_NAME,
                    "COMPETITOR_NAME": EntityType.COMPETITOR_NAME,
                }
                entity_type = mapping.get(type_key, EntityType.ENTITY_NAME)

                raw_val = item.get("value")
                if raw_val is None:
                    continue

                e = Entity(
                    entity_type=entity_type,
                    value=raw_val,
                    raw_text=str(raw_val),
                    confidence=float(item.get("confidence", 0.8)),
                    extraction_method="llm",
                )

                # Normalization
                try:
                    if entity_type == EntityType.AMOUNT:
                        e.normalized_value = normalize_amount(raw_val)
                    elif entity_type == EntityType.TIME_PERIOD:
                        e.normalized_value = normalize_time_period(raw_val)
                    elif entity_type == EntityType.METRIC:
                        e.normalized_value = normalize_metric(raw_val)
                except Exception:
                    # Leave normalized_value None on failure
                    pass

                entities.append(e)

        except Exception as ex:
            logger.warning("parse_llm_entities_failed", error=str(ex))

        return entities

    def _build_response(self, entities: List[Entity], user_input: str) -> ExtractedEntities:
        # Convenience accessors
        amount = None
        client_name = None
        date = None
        invoice_id = None
        metric = None
        problem_area = None
        time_period = None
        competitor = None
        target_value = None

        for entity in entities:
            if entity.entity_type == EntityType.AMOUNT and amount is None:
                try:
                    amount = entity.normalized_value or Decimal(str(entity.value))
                except Exception:
                    amount = None

            elif entity.entity_type == EntityType.CLIENT_NAME and client_name is None:
                client_name = entity.value

            elif entity.entity_type == EntityType.INVOICE_ID and invoice_id is None:
                invoice_id = entity.value

            elif entity.entity_type == EntityType.METRIC and metric is None:
                metric = entity.value

            elif entity.entity_type == EntityType.PROBLEM_AREA and problem_area is None:
                problem_area = entity.value

            elif entity.entity_type == EntityType.TIME_PERIOD and time_period is None:
                time_period = entity.normalized_value or entity.value

            elif entity.entity_type == EntityType.COMPETITOR_NAME and competitor is None:
                competitor = entity.value

            elif entity.entity_type == EntityType.TARGET_VALUE and target_value is None:
                target_value = entity.value

        avg_conf = (sum(e.confidence for e in entities) / len(entities)) if entities else 0.0

        return ExtractedEntities(
            entities=entities,
            amount=amount,
            client_name=client_name,
            date=date,
            invoice_id=invoice_id,
            metric=metric,
            problem_area=problem_area,
            time_period=time_period,
            competitor=competitor,
            target_value=target_value,
            total_entities=len(entities),
            confidence_score=avg_conf,
        )


# Singleton instance
entity_extractor = EntityExtractor()
