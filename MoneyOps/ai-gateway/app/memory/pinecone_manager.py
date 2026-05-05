"""
Pinecone Vector Store Integration for MoneyOps.
Provides persistent agent memory and RAG capabilities.
"""
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from pinecone import Pinecone, ServerlessSpec
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Pinecone config
PINECONE_API_KEY = "pcsk_27rmTB_31CQnh7Gfw72C2aPFmRaxAfqZSb94dt47gjgA4kWkMo5eRY651bEAkSfLBaJZFM"
PINECONE_INDEX_NAME = "moneyops-agent-memory"
PINECONE_HOST = "https://moneyops-9tizmhe.svc.aped-4627-b74a.pinecone.io"

# Namespaces for different data types
NAMESPACE_COMPLIANCE = "compliance-rules"    # GST rules, tax regulations
NAMESPACE_CLIENTS = "client-patterns"        # Payment behaviors
NAMESPACE_INVOICES = "invoice-history"       # Past invoices for context
NAMESPACE_CONVERSATIONS = "conversation-memory"  # Long-term agent memory


class PineconeManager:
    """
    Manages Pinecone vector database for agent memory and RAG.
    Uses llama-text-embed-v2 (hosted by Pinecone) for embeddings.
    """

    def __init__(self):
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index_name = PINECONE_INDEX_NAME
        self.host = PINECONE_HOST
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name, host=self.host)
        logger.info("pinecone_initialized", index=self.index_name)

    def _ensure_index_exists(self):
        """Create index if it doesn't exist"""
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1024,  # llama-text-embed-v2 dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info("pinecone_index_created", index=self.index_name)
        except Exception as e:
            logger.error("pinecone_index_error", error=str(e))

    async def store_memory(
        self,
        namespace: str,
        record_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a memory record in Pinecone.
        Pinecone auto-generates embeddings using llama-text-embed-v2.
        """
        try:
            record = {
                "id": record_id,
                "text": text,
            }
            if metadata:
                record["metadata"] = metadata
            
            self.index.upsert_records(
                namespace=namespace,
                records=[record]
            )
            
            logger.info(
                "memory_stored",
                namespace=namespace,
                record_id=record_id,
            )
            return True
        except Exception as e:
            logger.error("memory_store_error", error=str(e), namespace=namespace)
            return False

    async def search_memory(
        self,
        namespace: str,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memory using semantic similarity.
        Pinecone auto-converts query to vector using llama-text-embed-v2.
        """
        try:
            search_params = {
                "inputs": {"text": query},
                "top_k": top_k,
            }
            if filter:
                search_params["filter"] = filter
            
            results = self.index.search(
                namespace=namespace,
                query=search_params
            )
            
            # Parse results
            matches = []
            if hasattr(results, 'result') and results.result.hits:
                for hit in results.result.hits:
                    matches.append({
                        "id": hit.id,
                        "score": hit.score,
                        "text": hit.fields.get("text", ""),
                        "metadata": hit.fields.get("metadata", {}),
                    })
            
            logger.info(
                "memory_searched",
                namespace=namespace,
                query=query[:50],
                results=len(matches),
            )
            return matches
        except Exception as e:
            logger.error("memory_search_error", error=str(e), namespace=namespace)
            return []

    async def store_compliance_rule(
        self,
        rule_id: str,
        rule_text: str,
        rule_type: str,  # "gst", "tds", "filing"
        applicable_states: List[str] = None
    ) -> bool:
        """Store a compliance rule for RAG-powered queries"""
        metadata = {
            "type": "compliance_rule",
            "rule_type": rule_type,
            "applicable_states": applicable_states or [],
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.store_memory(
            namespace=NAMESPACE_COMPLIANCE,
            record_id=f"rule_{rule_id}",
            text=rule_text,
            metadata=metadata
        )

    async def store_client_pattern(
        self,
        client_id: str,
        client_name: str,
        payment_history: List[Dict[str, Any]]
    ) -> bool:
        """Store client payment behavior for predictive collections"""
        # Summarize payment behavior
        avg_days = 0
        on_time_count = 0
        for payment in payment_history:
            if payment.get("status") == "PAID":
                avg_days += payment.get("days_to_pay", 0)
                on_time_count += 1
        
        if on_time_count > 0:
            avg_days = avg_days / on_time_count
        
        text = f"Client: {client_name}. Average payment time: {avg_days:.0f} days. "
        text += f"Total invoices: {len(payment_history)}. "
        text += f"On-time payments: {on_time_count}."
        
        metadata = {
            "type": "client_pattern",
            "client_id": client_id,
            "client_name": client_name,
            "avg_days_to_pay": avg_days,
            "total_invoices": len(payment_history),
            "on_time_count": on_time_count,
            "risk_level": "high" if avg_days > 30 else "medium" if avg_days > 15 else "low",
        }
        
        return await self.store_memory(
            namespace=NAMESPACE_CLIENTS,
            record_id=f"client_{client_id}",
            text=text,
            metadata=metadata
        )

    async def search_similar_clients(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Find clients with similar payment patterns"""
        return await self.search_memory(
            namespace=NAMESPACE_CLIENTS,
            query=query,
            top_k=top_k
        )

    async def search_compliance_info(
        self,
        query: str,
        rule_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search compliance rules using RAG"""
        filter_dict = {}
        if rule_type:
            filter_dict["rule_type"] = rule_type
        
        return await self.search_memory(
            namespace=NAMESPACE_COMPLIANCE,
            query=query,
            top_k=top_k,
            filter=filter_dict if filter_dict else None
        )

    async def store_conversation_context(
        self,
        org_id: str,
        session_id: str,
        messages: List[Dict[str, str]]
    ) -> bool:
        """Store long-term conversation context"""
        text = " ".join([m.get("content", "") for m in messages])
        record_id = f"{org_id}_{session_id}_{datetime.utcnow().timestamp():.0f}"
        
        metadata = {
            "type": "conversation",
            "org_id": org_id,
            "session_id": session_id,
            "message_count": len(messages),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return await self.store_memory(
            namespace=NAMESPACE_CONVERSATIONS,
            record_id=record_id,
            text=text,
            metadata=metadata
        )


# Singleton instance
pinecone_manager = PineconeManager()
