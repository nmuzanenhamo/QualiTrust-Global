"""AI service for agentic verification assistant and fraud detection.

This module integrates with OpenAI's API to provide AI-powered analysis
of qualification credentials, detecting anomalies and potential fraud.
When the OpenAI API key is not available, it falls back to a rule-based
heuristic analysis engine.
"""

import json
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Qualification, User, VerificationMethod, VerificationRecord, VerificationResult


class AIService:
    """Service for AI-powered credential analysis and fraud detection."""

    @staticmethod
    def _heuristic_analysis(qualification: Qualification) -> dict:
        """Rule-based fallback analysis when OpenAI is not available."""
        anomalies = []
        risk_score = 0

        if not qualification.serial_number:
            anomalies.append("Missing serial number")
            risk_score += 20

        if not qualification.registration_number:
            anomalies.append("Missing registration number")
            risk_score += 15

        if qualification.date_expires:
            if qualification.date_expires < datetime.now(timezone.utc):
                anomalies.append("Qualification has expired")
                risk_score += 25

        if not qualification.holder_email and not qualification.holder_id_number:
            anomalies.append("No verifiable holder contact information")
            risk_score += 15

        institution = qualification.issuing_institution.lower()
        known_suspicious_patterns = ["diploma mill", "acme", "test university", "fake"]
        for pattern in known_suspicious_patterns:
            if pattern in institution:
                anomalies.append(f"Institution name matches suspicious pattern: '{pattern}'")
                risk_score += 40

        if qualification.qualification_type and "other" in str(qualification.qualification_type).lower():
            anomalies.append("Unclassified qualification type requires manual review")
            risk_score += 10

        confidence_score = max(0, 100 - risk_score)

        if risk_score >= 50:
            recommendation = "REJECT: High risk of fraud detected"
        elif risk_score >= 25:
            recommendation = "REVIEW: Moderate risk, manual verification recommended"
        else:
            recommendation = "APPROVE: Low risk, credential appears legitimate"

        return {
            "anomalies": anomalies,
            "risk_score": risk_score,
            "confidence_score": confidence_score,
            "recommendation": recommendation,
            "method": "heuristic",
        }

    @staticmethod
    async def _openai_analysis(qualification: Qualification) -> dict:
        """Use OpenAI API for credential analysis."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            prompt = f"""
            Analyze the following qualification credential for potential fraud or anomalies:

            Title: {qualification.title}
            Type: {qualification.qualification_type}
            Issuing Institution: {qualification.issuing_institution}
            Holder: {qualification.holder_name}
            Date Issued: {qualification.date_issued}
            Serial Number: {qualification.serial_number}
            Registration Number: {qualification.registration_number}

            Provide a JSON response with:
            - anomalies: list of detected anomalies
            - risk_score: 0-100 (higher = more risky)
            - confidence_score: 0-100 (higher = more confident in assessment)
            - recommendation: APPROVE, REVIEW, or REJECT with explanation
            """

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a credential verification expert. Analyze qualifications for fraud."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            result["method"] = "openai"
            return result

        except Exception:
            return AIService._heuristic_analysis(qualification)

    @staticmethod
    async def analyze_credential(
        db: Session,
        qualification_id: int,
        user: User,
    ) -> dict:
        """Analyze a credential using AI and create a verification record."""
        qualification = (
            db.query(Qualification)
            .filter(Qualification.id == qualification_id, Qualification.is_deleted == False)
            .first()
        )

        if not qualification:
            raise ValueError(f"Qualification with ID {qualification_id} not found")

        if settings.OPENAI_API_KEY:
            analysis = await AIService._openai_analysis(qualification)
        else:
            analysis = AIService._heuristic_analysis(qualification)

        confidence = analysis.get("confidence_score", 50)
        recommendation = analysis.get("recommendation", "")

        if "APPROVE" in recommendation.upper():
            result = VerificationResult.VERIFIED
        elif "REJECT" in recommendation.upper():
            result = VerificationResult.REJECTED
        else:
            result = VerificationResult.INCONCLUSIVE

        record = VerificationRecord(
            qualification_id=qualification.id,
            verified_by=user.id,
            method=VerificationMethod.AI_ASSISTED,
            result=result,
            notes=json.dumps(analysis, indent=2),
            ai_confidence_score=confidence,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "qualification_id": qualification.id,
            "anomalies": analysis.get("anomalies", []),
            "risk_score": analysis.get("risk_score", 0),
            "confidence_score": confidence,
            "recommendation": recommendation,
            "method": analysis.get("method", "heuristic"),
            "result": result.value,
            "verified_at": record.created_at,
        }
