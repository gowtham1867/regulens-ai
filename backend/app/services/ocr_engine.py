import os
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import io


class OCREngine:
    @staticmethod
    def calculate_file_hash(file_data) -> str:
        """Calculate SHA-256 cryptographic fingerprint from bytes or filepath."""
        if isinstance(file_data, str) and os.path.exists(file_data):
            with open(file_data, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        elif isinstance(file_data, str):
            return hashlib.sha256(file_data.encode("utf-8")).hexdigest()
        return hashlib.sha256(file_data).hexdigest()

    @staticmethod
    def inspect_file_authenticity(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate file binary headers, detect extension vs format mismatches,
        and assess basic structural integrity.
        """
        if not file_bytes or len(file_bytes) == 0:
            return {
                "is_valid": False,
                "detected_format": "EMPTY",
                "error": "Uploaded file is 0 bytes (empty file)."
            }

        safe_ext = os.path.splitext(filename)[1].lower()
        header = file_bytes[:16]

        detected_format = "UNKNOWN"
        if header.startswith(b"%PDF"):
            detected_format = "PDF"
        elif header.startswith(b"\x89PNG\r\n\x1a\n"):
            detected_format = "PNG"
        elif header.startswith(b"\xff\xd8\xff"):
            detected_format = "JPEG"
        elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
            detected_format = "GIF"
        elif header.startswith(b"RIFF") and b"WEBP" in header:
            detected_format = "WEBP"

        # Check for format vs declared extension mismatch
        expected_format = {
            ".pdf": "PDF",
            ".png": "PNG",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".webp": "WEBP",
        }.get(safe_ext, "OTHER")

        has_extension_mismatch = (
            detected_format != "UNKNOWN"
            and expected_format != "OTHER"
            and detected_format != expected_format
        )

        return {
            "is_valid": detected_format in ("PDF", "PNG", "JPEG", "WEBP"),
            "detected_format": detected_format,
            "declared_extension": safe_ext,
            "has_extension_mismatch": has_extension_mismatch,
            "file_size_bytes": len(file_bytes),
            "error": f"File extension '{safe_ext}' conflicts with actual binary header ({detected_format})" if has_extension_mismatch else None
        }

    @staticmethod
    def extract_from_file(file_path: str, filename: str) -> Dict[str, Any]:
        """
        Extract text, page count, and layout structures from PDF or images using PyMuPDF and PIL.
        Preserves page references and identifies digital vs raster scanned documents.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        safe_ext = os.path.splitext(filename)[1].lower()
        
        pages_text: List[Dict[str, Any]] = []
        combined_text = ""
        total_chars = 0
        is_scanned_image = False
        page_count = 1
        pdf_metadata: Dict[str, Any] = {}

        try:
            try:
                import pymupdf as fitz
            except ImportError:
                try:
                    import fitz
                except ImportError:
                    fitz = None

            if fitz is not None:
                doc = fitz.open(file_path)
                page_count = len(doc)
                if hasattr(doc, "metadata") and doc.metadata:
                    pdf_metadata = {
                        k: v for k, v in doc.metadata.items()
                        if v and k in ("title", "author", "creator", "producer", "creationDate", "modDate")
                    }

                for page_idx in range(page_count):
                    page = doc[page_idx]
                    text = page.get_text("text") or ""
                    cleaned_text = re.sub(r'\s+', ' ', text).strip()
                    total_chars += len(cleaned_text)

                    pages_text.append({
                        "page_number": page_idx + 1,
                        "text": cleaned_text,
                        "char_count": len(cleaned_text)
                    })
                    if cleaned_text:
                        combined_text += f"\n--- Page {page_idx + 1} ---\n" + cleaned_text

                doc.close()
            else:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                page_count = len(reader.pages)
                if reader.metadata:
                    pdf_metadata = {
                        k.lstrip('/'): str(v) for k, v in reader.metadata.items()
                        if v
                    }
                for page_idx, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    cleaned_text = re.sub(r'\s+', ' ', text).strip()
                    total_chars += len(cleaned_text)

                    pages_text.append({
                        "page_number": page_idx + 1,
                        "text": cleaned_text,
                        "char_count": len(cleaned_text)
                    })
                    if cleaned_text:
                        combined_text += f"\n--- Page {page_idx + 1} ---\n" + cleaned_text
        except Exception as e:
            # If PyMuPDF fails to open as a document, check if PIL can open as an image
            if safe_ext in (".png", ".jpg", ".jpeg", ".webp"):
                try:
                    with Image.open(file_path) as img:
                        w, h = img.size
                        pages_text.append({
                            "page_number": 1,
                            "text": "",
                            "char_count": 0,
                            "image_dims": f"{w}x{h}"
                        })
                        page_count = 1
                        is_scanned_image = True
                except Exception:
                    raise ValueError(f"Unable to read or parse file: {str(e)}")
            else:
                raise ValueError(f"Corrupted or invalid document format: {str(e)}")

        has_searchable_text = total_chars > 30
        if not has_searchable_text and safe_ext in (".png", ".jpg", ".jpeg"):
            is_scanned_image = True

        # Confidence based on character density, structure, and readability
        if total_chars > 200:
            confidence = 0.95
        elif total_chars > 60:
            confidence = 0.85
        elif has_searchable_text:
            confidence = 0.70
        else:
            confidence = 0.20

        extraction_method = "PYMUPDF_NATIVE_TEXT" if has_searchable_text else ("IMAGE_RASTER_SCAN" if is_scanned_image else "LOW_DENSITY_SCAN")

        return {
            "page_count": page_count,
            "raw_text": combined_text,
            "pages": pages_text,
            "total_chars": total_chars,
            "has_searchable_text": has_searchable_text,
            "is_scanned_image": is_scanned_image,
            "confidence": confidence,
            "extraction_method": extraction_method,
            "pdf_metadata": pdf_metadata
        }

    @staticmethod
    def classify_document_content(
        raw_text: str,
        declared_type: str,
        filename: str,
        is_scanned_image: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate uploaded document content against expected regulatory vocabulary.
        Flags document category mismatches (e.g. photos uploaded as land certificates,
        or resumes uploaded as fire safety clearances).
        """
        text_lower = (raw_text or "").lower()
        norm_type = declared_type.upper().strip()

        # Vocabulary dictionaries for regulatory categories
        KEYWORDS = {
            "FIRE_SAFETY_CERTIFICATE": [
                "fire", "noc", "rescue", "safety", "fire officer", "directorate of fire",
                "station officer", "fire fighting", "nbc", "evacuation", "hazard"
            ],
            "LAND_DOCUMENT": [
                "land", "deed", "title", "patta", "khasra", "survey", "acres", "hectares",
                "sub-registrar", "revenue", "ownership", "conveyance", "lease", "boundaries"
            ],
            "LAND_USE_CERTIFICATE": [
                "land use", "zoning", "change of land use", "clu", "revenue officer",
                "tahsildar", "collector", "institutional use", "educational use", "survey no"
            ],
            "BUILDING_PLAN": [
                "building plan", "sanction", "architect", "built up area", "floor area",
                "fsi", "far", "municipal", "town planning", "approved drawing"
            ],
            "OCCUPANCY_CERTIFICATE": [
                "occupancy certificate", "completion certificate", "fit for occupation",
                "municipal corporation", "local authority", "building completed"
            ],
            "AFFILIATION_CERTIFICATE": [
                "affiliation", "university", "sanction", "academic council", "syndicate",
                "approved intake", "provisional affiliation", "permanent affiliation", "registrar"
            ],
            "AFFILIATION_ORDER": [
                "affiliation", "university", "sanction order", "vice chancellor", "registrar",
                "intake", "courses approved", "notification"
            ],
            "AUDITED_FINANCIALS": [
                "balance sheet", "income and expenditure", "chartered accountant", "auditor",
                "udin", "ca firm", "assets", "liabilities", "corpus fund"
            ],
            "SOCIETY_TRUST_REGISTRATION": [
                "trust", "society", "societies registration", "memorandum of association",
                "charity commissioner", "public trust", "registration act"
            ]
        }

        # Anti-patterns (indicative of wrong documents like resumes, random photos)
        IRRELEVANT_PATTERNS = [
            ("RESUME_OR_CV", ["curriculum vitae", "resume", "objective", "skills:", "education:", "projects:", "hobbies:"]),
            ("SPORTS_OR_ENTERTAINMENT", ["fc barcelona", "camp nou", "stadium", "football", "ticket", "cinema", "concert"]),
            ("PERSONAL_ID_MISMATCH", ["passport", "driving licence", "aadhaar card", "voter id"]),
        ]

        detected_mismatch = None
        for irrelev_name, patterns in IRRELEVANT_PATTERNS:
            matches = sum(1 for p in patterns if p in text_lower)
            if matches >= 2:
                detected_mismatch = irrelev_name
                break

        # Filename hints of photo or personal file
        fn_lower = filename.lower()
        if any(w in fn_lower for w in ("photo", "crowd", "pic", "image", "stadium", "resume", "cv", "selfie")):
            if not any(k in text_lower for k in ("certificate", "aicte", "safety", "land", "affiliation")):
                detected_mismatch = "NON_REGULATORY_FILE"

        # Check keyword presence for declared document type
        canonical_key = norm_type
        if norm_type in ("LAND_DOCUMENTS", "LAND_USE_CERTIFICATE"):
            canonical_key = "LAND_DOCUMENT"
        elif norm_type == "AFFILIATION_ORDER":
            canonical_key = "AFFILIATION_CERTIFICATE"
        elif norm_type == "AUDIT_STATEMENT":
            canonical_key = "AUDITED_FINANCIALS"

        expected_kws = KEYWORDS.get(canonical_key, [])
        match_count = sum(1 for kw in expected_kws if kw in text_lower)

        is_plausible = True
        mismatch_reason = None

        if detected_mismatch:
            is_plausible = False
            mismatch_reason = (
                f"Uploaded file appears to be a '{detected_mismatch.replace('_', ' ').title()}' "
                f"rather than the declared '{norm_type.replace('_', ' ')}'."
            )
        elif len(raw_text.strip()) > 100 and expected_kws and match_count == 0:
            is_plausible = False
            mismatch_reason = (
                f"Document text contains no relevant terminology for a '{norm_type.replace('_', ' ')}'. "
                f"Possible document type mismatch."
            )
        elif is_scanned_image and len(raw_text.strip()) == 0:
            # File is an image with no text
            is_plausible = False
            mismatch_reason = (
                f"Uploaded file is a photographic image with no machine-readable text or regulatory seals. "
                f"Cannot verify as a valid '{norm_type.replace('_', ' ')}'."
            )

        return {
            "is_plausible": is_plausible,
            "is_mismatch": not is_plausible,
            "declared_type": norm_type,
            "matched_keywords_count": match_count,
            "detected_mismatch": detected_mismatch,
            "mismatch_reason": mismatch_reason,
            "reasoning": mismatch_reason or ""
        }

    @staticmethod
    def extract_structured_fields(
        document_type: str,
        raw_text: str,
        pages: List[Dict[str, Any]],
        declared_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract deterministic, typed fields using pattern recognition, regex heuristics,
        and positional matching across pages according to the document category schema.
        """
        extracted_fields: List[Dict[str, Any]] = []
        doc_type = (declared_type or document_type).upper().strip()

        def find_in_pages(regex_pattern: str, flags=re.IGNORECASE) -> Optional[Tuple[str, int, str]]:
            for p in pages:
                text_content = p.get("text", "")
                if not text_content:
                    continue
                match = re.search(regex_pattern, text_content, flags)
                if match:
                    val = match.group(1).strip()
                    start = max(0, match.start() - 40)
                    end = min(len(text_content), match.end() + 40)
                    excerpt = text_content[start:end]
                    return val, p.get("page_number", 1), excerpt
            return None

        # -------------------------------------------------------------------------
        # COMMON REGULATORY FIELDS (Applicable across all official submissions)
        # -------------------------------------------------------------------------
        
        # 1. Certificate / Reference / Order / Registration Number
        cert_match = find_in_pages(r'(?:NOC\s*(?:No|Number)|Fire\s*NOC|Certificate\s*(?:No|Number)|Ref(?:erence)?\s*(?:No|Number)|Document\s*No|Reg(?:istration)?\s*No|Order\s*No)[:.\s-]*([A-Z0-9\/-]{4,35})')
        if not cert_match:
            cert_match = find_in_pages(r'\b([A-Z]{2,5}-[A-Z0-9]{2,6}-\d{4}-\d{3,6})\b')
        if not cert_match:
            cert_match = find_in_pages(r'\b(NOC-[A-Z0-9\/-]{5,25})\b')
        if not cert_match:
            cert_match = find_in_pages(r'\b(REV-[A-Z0-9\/-]{5,25})\b')

        if cert_match:
            extracted_fields.append({
                "field_key": "certificate_number",
                "field_label": "Certificate / Reference Number",
                "extracted_value": cert_match[0],
                "normalized_value": cert_match[0].upper().replace(" ", ""),
                "source_page": cert_match[1],
                "confidence": 0.95,
                "excerpt": cert_match[2],
                "extraction_method": "REGEX_PATTERN"
            })

        # 2. Institution / College Name
        inst_match = find_in_pages(r'(?:Institution\s*Name|College\s*Name|Name\s*of\s*the\s*Institution|Name\s*of\s*Institute)[:.\s-]*([A-Za-z0-9\s&,.-]{6,70}(?:Institute|College|University|Technology|Engineering|Polytechnic|Campus|Academy|Foundation))')
        if not inst_match:
            inst_match = find_in_pages(r'\b((?:Apex|Zenith|Vanguard|National|Government|Global|Bharath|St\.\s*Mary\'s|Imperial|Sunrise)\s+[A-Za-z0-9\s&,.-]{4,50}(?:Institute|College|Technology|Engineering|Polytechnic|Academy)?)\b')

        if inst_match:
            extracted_fields.append({
                "field_key": "institution_name",
                "field_label": "Institution Name",
                "extracted_value": inst_match[0],
                "normalized_value": inst_match[0].strip().title(),
                "source_page": inst_match[1],
                "confidence": 0.92,
                "excerpt": inst_match[2],
                "extraction_method": "REGEX_PATTERN"
            })

        # 3. AICTE Permanent Institute ID
        aicte_id_match = find_in_pages(r'(?:AICTE\s*ID|PID|Permanent\s*Institute\s*ID)[:.\s-]*([1-9]-\d{7,10})')
        if aicte_id_match:
            extracted_fields.append({
                "field_key": "aicte_id",
                "field_label": "AICTE Permanent ID",
                "extracted_value": aicte_id_match[0],
                "normalized_value": aicte_id_match[0].strip(),
                "source_page": aicte_id_match[1],
                "confidence": 0.98,
                "excerpt": aicte_id_match[2],
                "extraction_method": "REGEX_PATTERN"
            })

        # 4. Issue Date / Dated
        issue_date_match = find_in_pages(r'(?:Date\s*of\s*Issue|Issued\s*on|Issue\s*Date|Dated|Date)[:.\s-]*([0-3]?\d[\/-][0-1]?\d[\/-]\d{4}|\d{4}-\d{2}-\d{2})')
        if issue_date_match:
            extracted_fields.append({
                "field_key": "issue_date",
                "field_label": "Issue Date",
                "extracted_value": issue_date_match[0],
                "normalized_value": OCREngine.normalize_date(issue_date_match[0]),
                "source_page": issue_date_match[1],
                "confidence": 0.94,
                "excerpt": issue_date_match[2],
                "extraction_method": "REGEX_PATTERN"
            })

        # 5. Expiry Date / Valid Upto Date
        expiry_date_match = find_in_pages(r'(?:Valid\s*Upto|Expiry\s*Date|Valid\s*Through|Expires\s*on|Valid\s*till|Validity\s*Period)[:.\s-]*([0-3]?\d[\/-][0-1]?\d[\/-]\d{4}|\d{4}-\d{2}-\d{2})')
        if expiry_date_match:
            extracted_fields.append({
                "field_key": "expiry_date",
                "field_label": "Expiry / Valid Upto Date",
                "extracted_value": expiry_date_match[0],
                "normalized_value": OCREngine.normalize_date(expiry_date_match[0]),
                "source_page": expiry_date_match[1],
                "confidence": 0.94,
                "excerpt": expiry_date_match[2],
                "extraction_method": "REGEX_PATTERN"
            })

        # -------------------------------------------------------------------------
        # CATEGORY-SPECIFIC STRUCTURED FIELD SCHEMAS
        # -------------------------------------------------------------------------

        # A. FIRE SAFETY CERTIFICATE / NOC
        if doc_type in ("FIRE_SAFETY_CERTIFICATE", "FIRE"):
            noc_match = find_in_pages(r'(?:NOC\s*(?:No|Number)|Fire\s*NOC)[:.\s-]*([A-Z0-9\/-]{4,35})')
            if noc_match:
                extracted_fields.append({
                    "field_key": "noc_number",
                    "field_label": "Fire NOC Number",
                    "extracted_value": noc_match[0],
                    "normalized_value": noc_match[0].upper().replace(" ", ""),
                    "source_page": noc_match[1],
                    "confidence": 0.98,
                    "excerpt": noc_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            valid_to_match = find_in_pages(r'(?:Valid\s*(?:Upto|To|Through|Till)|Expires\s*on)[:.\s-]*([0-3]?\d[\/-][0-1]?\d[\/-]\d{4}|\d{4}-\d{2}-\d{2})')
            if valid_to_match:
                extracted_fields.append({
                    "field_key": "valid_to",
                    "field_label": "Valid Upto Date",
                    "extracted_value": valid_to_match[0],
                    "normalized_value": OCREngine.normalize_date(valid_to_match[0]),
                    "source_page": valid_to_match[1],
                    "confidence": 0.96,
                    "excerpt": valid_to_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            auth_match = find_in_pages(r'(Directorate\s*of\s*Fire(?:\s*and|\s*&)\s*Rescue\s*Services|Department\s*of\s*Fire\s*Services|Fire\s*Services\s*Department|Divisional\s*Fire\s*Officer|Municipal\s*Corporation|State\s*Disaster\s*Management)')
            if auth_match:
                extracted_fields.append({
                    "field_key": "issuing_authority",
                    "field_label": "Issuing Authority",
                    "extracted_value": auth_match[0],
                    "normalized_value": auth_match[0].strip(),
                    "source_page": auth_match[1],
                    "confidence": 0.96,
                    "excerpt": auth_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            compliance_match = find_in_pages(r'(NBC\s*2016|National\s*Building\s*Code|Part\s*4\s*Fire\s*and\s*Life\s*Safety)')
            if compliance_match:
                extracted_fields.append({
                    "field_key": "compliance_standard",
                    "field_label": "Fire Safety Code Standard",
                    "extracted_value": compliance_match[0],
                    "normalized_value": compliance_match[0].strip(),
                    "source_page": compliance_match[1],
                    "confidence": 0.90,
                    "excerpt": compliance_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

        # B. LAND DOCUMENTS & LAND USE CERTIFICATES
        elif doc_type in ("LAND_DOCUMENT", "LAND_DOCUMENTS", "LAND_USE_CERTIFICATE", "LAND"):
            area_match = find_in_pages(r'(?:Total\s*Land\s*Area|Area\s*of\s*Land|Land\s*Measure|Extent\s*of\s*Land)[:.\s-]*([0-9]+(?:\.[0-9]+)?)\s*(Acres?|Hectares?|Sq\.\s*Meters?|Cents?)')
            if area_match:
                extracted_fields.append({
                    "field_key": "land_area",
                    "field_label": "Total Land Area",
                    "extracted_value": f"{area_match[0]} {area_match[2] if len(area_match) > 2 else 'Acres'}",
                    "normalized_value": area_match[0],
                    "source_page": area_match[1],
                    "confidence": 0.95,
                    "excerpt": area_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            survey_match = find_in_pages(r'(?:Survey\s*No|Khasra\s*No|Plot\s*No|Gata\s*No|Dag\s*No)[:.\s-]*([0-9A-Za-z\/-]+)')
            if survey_match:
                extracted_fields.append({
                    "field_key": "survey_number",
                    "field_label": "Survey / Khasra Number",
                    "extracted_value": survey_match[0],
                    "normalized_value": survey_match[0].strip().upper(),
                    "source_page": survey_match[1],
                    "confidence": 0.91,
                    "excerpt": survey_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            auth_match = find_in_pages(r'(Sub-Registrar\s*Office|Department\s*of\s*Revenue|Tahsildar|District\s*Collector|Revenue\s*Divisional\s*Officer)')
            if auth_match:
                extracted_fields.append({
                    "field_key": "issuing_authority",
                    "field_label": "Issuing Revenue Authority",
                    "extracted_value": auth_match[0],
                    "normalized_value": auth_match[0].strip(),
                    "source_page": auth_match[1],
                    "confidence": 0.92,
                    "excerpt": auth_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            zoning_match = find_in_pages(r'(Educational\s*Use|Institutional\s*Use|Public\s*and\s*Semi-Public|Residential\s*Converted)')
            if zoning_match:
                extracted_fields.append({
                    "field_key": "land_use_classification",
                    "field_label": "Permitted Land Use Classification",
                    "extracted_value": zoning_match[0],
                    "normalized_value": zoning_match[0].strip(),
                    "source_page": zoning_match[1],
                    "confidence": 0.93,
                    "excerpt": zoning_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

        # C. UNIVERSITY AFFILIATION CERTIFICATE / SANCTION ORDER
        elif doc_type in ("AFFILIATION_CERTIFICATE", "AFFILIATION_ORDER", "AFFILIATION"):
            univ_match = find_in_pages(r'(Anna\s*University|Visvesvaraya\s*Technological\s*University|Jawaharlal\s*Nehru\s*Technological\s*University|Mumbai\s*University|Delhi\s*Technological\s*University|Dr\.\s*A\.P\.J\.\s*Abdul\s*Kalam\s*Technical\s*University|[A-Za-z\s]+University)')
            if univ_match:
                extracted_fields.append({
                    "field_key": "affiliating_university",
                    "field_label": "Affiliating University",
                    "extracted_value": univ_match[0],
                    "normalized_value": univ_match[0].strip(),
                    "source_page": univ_match[1],
                    "confidence": 0.94,
                    "excerpt": univ_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            intake_match = find_in_pages(r'(?:Approved\s*Intake|Total\s*Sanctioned\s*Intake|Approved\s*Seats|Sanctioned\s*Seats)[:.\s-]*([0-9]{2,4})')
            if intake_match:
                extracted_fields.append({
                    "field_key": "approved_intake",
                    "field_label": "Approved Student Intake",
                    "extracted_value": intake_match[0],
                    "normalized_value": intake_match[0].strip(),
                    "source_page": intake_match[1],
                    "confidence": 0.92,
                    "excerpt": intake_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            ay_match = find_in_pages(r'(?:Academic\s*Year|Session)[:.\s-]*([2][0][2-9][0-9]-[2][0][2-9][0-9])')
            if ay_match:
                extracted_fields.append({
                    "field_key": "academic_year",
                    "field_label": "Approved Academic Year",
                    "extracted_value": ay_match[0],
                    "normalized_value": ay_match[0].strip(),
                    "source_page": ay_match[1],
                    "confidence": 0.95,
                    "excerpt": ay_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

        # D. BUILDING PLAN APPROVAL & OCCUPANCY CERTIFICATE
        elif doc_type in ("BUILDING_PLAN", "OCCUPANCY_CERTIFICATE"):
            area_match = find_in_pages(r'(?:Total\s*Built-?up\s*Area|Built-?up\s*Area|Plinth\s*Area|Covered\s*Area)[:.\s-]*([0-9]+(?:\.[0-9]+)?)\s*(Sq\.\s*Meters?|Sq\.\s*Ft|sqm|sqft)')
            if area_match:
                extracted_fields.append({
                    "field_key": "built_up_area_sqm",
                    "field_label": "Total Built-Up Area",
                    "extracted_value": f"{area_match[0]} {area_match[2]}",
                    "normalized_value": area_match[0],
                    "source_page": area_match[1],
                    "confidence": 0.93,
                    "excerpt": area_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            authority_match = find_in_pages(r'(Municipal\s*Corporation|Town\s*Planning\s*Authority|Development\s*Authority|Directorate\s*of\s*Town\s*and\s*Country\s*Planning|Gram\s*Panchayat)')
            if authority_match:
                extracted_fields.append({
                    "field_key": "issuing_authority",
                    "field_label": "Approving Urban Planning Authority",
                    "extracted_value": authority_match[0],
                    "normalized_value": authority_match[0].strip(),
                    "source_page": authority_match[1],
                    "confidence": 0.91,
                    "excerpt": authority_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

        # E. AUDITED FINANCIAL STATEMENTS
        elif doc_type in ("AUDITED_FINANCIALS", "AUDIT_STATEMENT", "AUDIT"):
            ca_match = find_in_pages(r'(?:Chartered\s*Accountants?|Auditors?)[:.\s-]*([A-Za-z0-9\s&,.-]{4,50}(?:Associates|LLP|Co\.))')
            if ca_match:
                extracted_fields.append({
                    "field_key": "ca_firm_name",
                    "field_label": "Auditing CA Firm",
                    "extracted_value": ca_match[0],
                    "normalized_value": ca_match[0].strip(),
                    "source_page": ca_match[1],
                    "confidence": 0.92,
                    "excerpt": ca_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

            udin_match = find_in_pages(r'(?:UDIN)[:.\s-]*([0-9A-Z]{18})')
            if udin_match:
                extracted_fields.append({
                    "field_key": "ca_udin",
                    "field_label": "ICAI UDIN Number",
                    "extracted_value": udin_match[0],
                    "normalized_value": udin_match[0].strip(),
                    "source_page": udin_match[1],
                    "confidence": 0.99,
                    "excerpt": udin_match[2],
                    "extraction_method": "REGEX_PATTERN"
                })

        return extracted_fields

    @classmethod
    def extract_and_structure(cls, file_path: str, declared_type: str, filename: str = None) -> tuple:
        """Convenience method combining extraction, classification, and field parsing."""
        if not filename:
            filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            f_bytes = f.read()
        auth_info = cls.inspect_file_authenticity(f_bytes, filename)
        if not auth_info.get("is_valid"):
            return "", [], {"is_valid": False, "category_mismatch": False, "warning": auth_info.get("error")}, auth_info

        extract_res = cls.extract_from_file(file_path, filename)
        classify_res = cls.classify_document_content(
            extract_res["raw_text"], declared_type, filename, extract_res.get("is_scanned_image", False)
        )
        fields = cls.extract_structured_fields(declared_type, extract_res["raw_text"], extract_res.get("pages", []))

        meta = {
            "page_count": extract_res.get("page_count", 1),
            "total_chars": extract_res.get("total_chars", 0),
            "is_raster_only": not extract_res.get("has_searchable_text", False),
            "category_mismatch": not classify_res.get("is_plausible", True),
            "classification_reasoning": classify_res.get("mismatch_reason") or classify_res.get("reasoning", ""),
            "confidence": extract_res.get("confidence", 0.0),
            "extraction_method": extract_res.get("extraction_method", ""),
            "warning": "Raster image scan without digital text" if not extract_res.get("has_searchable_text", False) else None
        }
        return extract_res["raw_text"], fields, meta, auth_info

    @staticmethod
    def normalize_date(date_str: str) -> str:
        """Standardize various date representations into ISO YYYY-MM-DD."""
        date_str = date_str.strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        return date_str


ocr_engine = OCREngine()
