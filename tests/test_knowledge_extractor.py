"""Tests for KnowledgeExtractor."""

from cascade.core.knowledge_extractor import KnowledgeExtractor
from cascade.models.enums import KnowledgeStatus
from cascade.models.knowledge import ADR, Pattern


def test_extract_pattern_proposal():
    extractor = KnowledgeExtractor()
    response = """
Executing the ticket.
<knowledge_proposal>
type: PATTERN
name: Singleton Pattern
description: Ensures a class has only one instance.
template: |
  class Singleton:
      _instance = None
      def __new__(cls):
          if not cls._instance:
              cls._instance = super().__new__(cls)
          return cls._instance
tags: [singleton, pattern]
examples: [utils.py]
</knowledge_proposal>
Done.
"""
    proposals = extractor.extract_proposals(response, ticket_id=1)

    assert len(proposals) == 1
    p = proposals[0]
    assert isinstance(p, Pattern)
    assert p.pattern_name == "Singleton Pattern"
    assert p.status == KnowledgeStatus.PROPOSED
    assert p.learned_from_ticket_id == 1
    assert "singleton" in p.applies_to_tags
    assert "utils.py" in p.file_examples


def test_extract_adr_proposal():
    extractor = KnowledgeExtractor()
    response = """
<knowledge_proposal>
type: ADR
title: Use FastAPI instead of Flask
context: We need high performance and async support.
decision: We will use FastAPI.
rationale: Pydantic integration and async/await support are superior.
consequences: Faster development, better validation.
alternatives: Flask, Django
</knowledge_proposal>
"""
    proposals = extractor.extract_proposals(response, ticket_id=42)

    assert len(proposals) == 1
    a = proposals[0]
    assert isinstance(a, ADR)
    assert a.title == "Use FastAPI instead of Flask"
    assert a.status == KnowledgeStatus.PROPOSED
    assert a.created_by_ticket_id == 42
    assert "Pydantic" in a.rationale


def test_extract_multiple_proposals():
    extractor = KnowledgeExtractor()
    response = """
<knowledge_proposal>
---
type: PATTERN
name: P1
description: D1
---
type: ADR
title: A1
context: C1
decision: Dec1
rationale: R1
</knowledge_proposal>
"""
    proposals = extractor.extract_proposals(response)

    assert len(proposals) == 2
    assert isinstance(proposals[0], Pattern)
    assert isinstance(proposals[1], ADR)


def test_extract_no_proposal():
    extractor = KnowledgeExtractor()
    response = "No proposal here."
    proposals = extractor.extract_proposals(response)
    assert len(proposals) == 0


def test_extract_malformed_proposal():
    extractor = KnowledgeExtractor()
    response = """
<knowledge_proposal>
this is not yaml: [
</knowledge_proposal>
"""
    proposals = extractor.extract_proposals(response)
    assert len(proposals) == 0
