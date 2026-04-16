# """
# Zero-Shot NER Agent for MoneyOps
# Extracts ALL entities from natural language in a single pass.
# Handles multi-line items, fuzzy client matching, and complex utterances.
# """

# import re
# import json
# from typing import Dict, Any, List, Optional, Tuple
# from dataclasses import dataclass, field
# from decimal import Decimal
# import asyncio

# from app.llm.groq_client import groq_client
# from app.utils.logger import get_logger
# from app.adapters.backend_adapter import get_backend_adapter

# logger = get_logger(__name__)


# @dataclass
# class LineItem:
#     """Represents a single line item in an invoice"""
#     description: str
#     quantity: int = 1
#     unit_price: Optional[Decimal] = None
#     total: Optional[Decimal] = None
#     item_type: str = "SERVICE"  # SERVICE or PRODUCT


# @dataclass
# class ExtractedInvoiceData:
#     """Complete invoice data extracted from natural language"""
#     client_name: Optional[str] = None
#     client_id: Optional[str] = None
#     line_items: List[LineItem] = field(default_factory=list)
#     total_amount: Optional[Decimal] = None
#     gst_applicable: bool = True
#     gst_percent: float = 18.0
#     due_days: Optional[int] = None
#     due_date: Optional[str] = None
#     notes: Optional[str] = None
#     confidence: float = 0.0
    
#     # Fuzzy match metadata
#     client_match_confidence: float = 0.0
#     client_candidates: List[Dict[str, Any]] = field(default_factory=list)


# class NERAgent:
#     """
#     Zero-Shot Named Entity Recognition Agent
    
#     Capabilities:
#     - Extract multiple line items frt name
#  match clien: Fuzzy Step 3 # 
#               ", []))
# ne_itemset("lies.graw_entitine_items(parse_liself._ms = iteine_      ltems
#   ne i 2: Parse liep        # St
        
# ext)erance, contties(uttact_all_entillm_extrelf._es = await sntiti    raw_eion
#      extractsed entity LLM-ba   # Step 1:
#           ])
#    nce[:100ce=uttera utteranion_start",act("ner_extrger.info log
#            """"
#     ente developmebsits for w0000 rupeerp 5 Coll Acme  - "Bie"
#       ice fe and a servptopsfor 10 laft oice Microso    - "Inv    nsulting"
#  hours of co0 each and 220ervers at $or 5 cloud sDarsh f for nvoice ireate an"C      - 
#   uts:inple  Examp 
       
#        language.ral rom natudata fe invoice omplet  Extract c"
#            ""ata:
#    eDvoicdIn Extracte
#     ) ->] = Noner, Any][Dict[sttionalt: Op contex     one,
#   [str] = Nnaler_id: Optio
#         usd: str,_iorg      : str,
#     utterance,
#               self
# entities(nvoice_xtract_if ec de   asyn
#       _client
#    oq = groq    self.grer()
#     _adaptkend= get_bacelf.backend         s(self):
# _init__  def _
    
#   ""   "
#  ressionsexpnancial complex fiParse  - 
#    rsh -> Dash) errors (Dascriptiontrane Handl    - RM
#  against Cent namesclimatch   - Fuzzy 
#   ancetterom single u