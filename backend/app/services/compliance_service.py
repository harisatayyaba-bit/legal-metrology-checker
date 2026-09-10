import re
import logging
from typing import List, Tuple, Optional
from app.schemas.scan_schema import FieldCompliance, ComplianceReport, ComplianceVerdict

logger = logging.getLogger(__name__)

# Keywords for commodity categorization
FOOD_KEYWORDS = {
    "food", "edible", "grocery", "snack", "snacks", "beverage", "drink", "tea", "coffee",
    "ghee", "cooking oil", "edible oil", "vegetable oil", "mustard oil", "sunflower oil",
    "groundnut oil", "olive oil", "soybean oil", "palm oil", "sesame oil",
    "dairy butter", "table butter", "peanut butter",
    "cheese", "paneer", "curd", "yogurt", "dairy cream", "ice cream",
    "biscuit", "biscuits", "cookie", "cookies", "bread", "bakery", "cake", "rusk",
    "flour", "atta", "maida", "besan", "suji", "rice", "wheat", "dal", "pulses", "grain",
    "spice", "spices", "masala", "chilli", "turmeric", "coriander", "cumin", "pepper",
    "sugar", "salt", "jaggery", "honey", "chocolate", "candy", "sweet", "sweets",
    "confectionery", "jam", "pickle", "sauce", "ketchup", "noodles", "pasta", "cereal",
    "oats", "cornflakes", "juice", "squash", "syrup", "chips", "namkeen", "nuts", "cashew",
    "milk", "dairy", "infant formula", "baby food"
}

# Strong non-food signals — these override generic food words like 'cream', 'oil', 'milk' (in lotion names)
NON_FOOD_STRONG_KEYWORDS = {
    # Skincare / Cosmetics / Personal Care
    "skincare", "skin care", "face care", "body care",
    "face wash", "facewash", "face cleanser", "facial cleanser",
    "face cream", "skin cream", "cold cream", "day cream", "night cream", "eye cream",
    "moisturizer", "moisturiser", "moisturizing cream", "moisturising cream",
    "serum", "face serum", "facial serum", "body serum",
    "toner", "face toner", "face mist", "face spray",
    "sunscreen", "sun screen", "sunblock", "sun protection", "spf",
    "face scrub", "body scrub", "exfoliator", "face pack", "face mask", "sheet mask",
    "lip balm", "lipstick", "lip gloss", "lip tint", "kajal", "kohl", "eyeliner",
    "mascara", "eyeshadow", "foundation", "concealer", "makeup primer",
    "compact powder", "loose powder", "blush", "bronzer", "highlighter",
    "makeup", "make-up", "bb cream", "cc cream",
    "body lotion", "body butter", "body oil", "body wash", "shower gel", "bath gel",
    "shampoo", "conditioner", "hair conditioner", "hair oil", "hair serum",
    "hair gel", "hair wax", "hair color", "hair dye", "hair spray", "hair mask",
    "eau de parfum", "eau de toilette", "cologne", "body spray", "body mist",
    "deodorant", "roll on", "talcum powder",
    "aftershave", "shaving cream", "shaving foam", "shaving gel",
    "toothpaste", "mouthwash",
    "bathing bar", "beauty bar", "toilet soap", "handwash", "hand sanitizer",
    "nail polish", "nail enamel", "nail paint", "nail remover",
    "dermatological", "dermatologist tested", "hypoallergenic",
    "salicylic acid", "hyaluronic acid", "niacinamide", "retinol", "glycolic acid",
    "vitamin c serum", "anti-aging", "anti-wrinkle", "anti-acne",
    "skin whitening", "skin brightening", "skin lightening", "skin radiance",
    "hydrating serum", "brightening serum", "collagen", "peptide", "keratin",
    # Household Cleaners
    "detergent", "laundry", "washing powder", "dishwash", "dishwashing",
    "surface cleaner", "floor cleaner", "toilet cleaner", "glass cleaner",
    "fabric softener", "fabric conditioner", "stain remover", "bleach",
    "disinfectant", "air freshener", "mosquito repellent", "insecticide",
    # Other Non-Food
    "cosmetic", "cosmetics", "perfume", "apparel", "garment",
    "lubricant", "motor oil", "engine oil", "paint", "varnish",
    "adhesive", "glue", "fertilizer", "pesticide", "battery",
    "stationery", "pen", "pencil",
}

# Generic non-food secondary keywords (only count if no food context)
NON_FOOD_KEYWORDS = NON_FOOD_STRONG_KEYWORDS | {
    "soap", "lotion", "sanitizer", "cleanser", "conditioner",
    "chemical", "acid", "bulb", "lamp", "wire", "hardware",
    "cement", "plastic", "cloth", "towel", "shoe", "polish",
    "notebook", "paper",
}


class ComplianceService:
    """
    Validates extracted packaged commodity declarations against the
    Legal Metrology (Packaged Commodities) Rules, 2011 (DoCA - SIH 26034).
    """

    def detect_commodity_type(self, full_text: str, lines: List[str]) -> Tuple[bool, str]:
        """
        Detects whether commodity is a food/edible item or a non-food
        household/chemical/cosmetic/personal-care product.
        Returns (is_food, classification_label).
        """
        text_lower = full_text.lower()
        has_fssai_explicit = "fssai" in text_lower or bool(re.search(r"\b[12]\d{13}\b", text_lower))

        # Strong non-food keywords immediately classify regardless of ambiguous food words
        has_strong_non_food = any(k in text_lower for k in NON_FOOD_STRONG_KEYWORDS)
        has_non_food = has_strong_non_food or any(k in text_lower for k in NON_FOOD_KEYWORDS)
        has_food = any(k in text_lower for k in FOOD_KEYWORDS)

        if has_fssai_explicit:
            return True, "Food / FSSAI Claimed"
        # Strong non-food signals win even if ambiguous food words (e.g. "cream", "oil") are present
        if has_strong_non_food:
            return False, "Non-Food (Cosmetics / Skincare / Personal Care / Household)"
        if has_non_food and not has_food:
            return False, "Non-Food (Household / Chemical / Personal Care)"
        if has_food:
            return True, "Food / Edible Commodity"

        # Default fallback for general packaged commodities
        return True, "General Packaged Commodity"

    def evaluate_compliance(self, raw_text: str, lines: List[str]) -> ComplianceReport:
        norm_text = raw_text.lower()
        full_text_joined = " \n ".join(lines).lower()

        # Check commodity classification
        is_food_product, commodity_label = self.detect_commodity_type(norm_text, lines)

        # Evaluate the statutory checks
        mfg_check = self._check_manufacturer(lines, norm_text)
        qty_check = self._check_net_quantity(lines, norm_text)
        mrp_check = self._check_mrp(lines, norm_text)
        date_check = self._check_mfg_date(lines, norm_text)
        care_check = self._check_consumer_care(lines, norm_text)

        all_fields = [mfg_check, qty_check, mrp_check, date_check, care_check]

        # FSSAI check only applies to food/edible goods or if FSSAI is explicitly claimed on packaging
        if is_food_product:
            fssai_check = self._check_fssai(lines, norm_text, is_food_product=True)
            all_fields.append(fssai_check)

        passed_count = sum(1 for f in all_fields if f.verdict == ComplianceVerdict.COMPLIANT.value)
        advisory_count = sum(1 for f in all_fields if f.verdict == ComplianceVerdict.ADVISORY.value)
        failed_count = sum(1 for f in all_fields if f.verdict == ComplianceVerdict.NON_COMPLIANT.value)

        # Determine Overall 3-tier Verdict
        if failed_count > 0:
            overall_verdict = ComplianceVerdict.NON_COMPLIANT.value
            summary = f"Label non-compliant: {failed_count} mandatory declaration(s) missing or violating statutory rules."
        elif advisory_count > 0:
            overall_verdict = ComplianceVerdict.ADVISORY.value
            summary = f"Label is technically compliant with {advisory_count} packaging advisory note(s) for optimization."
        else:
            overall_verdict = ComplianceVerdict.COMPLIANT.value
            summary = "Label is fully compliant with all Legal Metrology (Packaged Commodities) Rules, 2011."

        return ComplianceReport(
            overall_verdict=overall_verdict,
            summary=summary,
            total_checks=len(all_fields),
            passed_checks=passed_count,
            advisory_checks=advisory_count,
            failed_checks=failed_count,
            fields=all_fields,
        )

    def _check_manufacturer(self, lines: List[str], full_text: str) -> FieldCompliance:
        """Rule 6(1)(a): Name and complete address of the manufacturer / packer / importer."""
        field_id = "manufacturer_address"
        field_name = "Manufacturer / Packer Name & Address"
        rule_ref = "Legal Metrology Rules 2011, Rule 6(1)(a)"

        mfg_pattern = re.compile(
            r"\b("
            r"manufactured\s*(?:&|and)\s*marketed\s*by"
            r"|packed\s*(?:&|and)\s*marketed\s*by"
            r"|imported\s*(?:&|and)\s*marketed\s*by"
            r"|manufac(?:tured|\s+tured|ture)?\s*by"
            r"|mfg\.?\s*by"
            r"|packed\s*by"
            r"|pac\s*ked\s*by"
            r"|pkd\.?\s*by"
            r"|marketed\s*by"
            r"|mkt[d]?\.?\s*by"
            r"|imported\s*by"
            r"|manufacturer\s*:"
            r"|packer\s*:"
            r"|importer\s*:"
            r")\s*[:\-]?(.*)",
            re.IGNORECASE
        )
        pin_pattern = re.compile(r"(?<!\d)[1-9][0-9]{5}(?!\d)")

        # Boundaries separating manufacturer declarations from other statutory declarations
        other_decl_pattern = re.compile(
            r"\b("
            r"mrp|maximum\s*retail\s*price|max\.?\s*retail"
            r"|net\s*(?:wt|weight|qty|quantity|vol|volume|content[s]?|mass)"
            r"|mfg\.?\s*date|pkd\.?\s*date|date\s*of\s*(?:mfg|pack)"
            r"|exp\.?\s*date|best\s*before|use\s*by"
            r"|consumer\s*care|customer\s*care|helpline|toll\s*free|care@|help@"
            r"|fssai|lic\.?\s*no|license\s*no"
            r"|batch\s*no|lot\s*no|b\.?\s*no"
            r"|ingredients\s*:|serving\s*size|nutrition"
            r"|caution|warning|directions"
            r")\b",
            re.IGNORECASE
        )

        address_keywords_pattern = re.compile(
            r"\b("
            r"regd\.?\s*(?:off(?:ice)?|addr(?:ess)?)"
            r"|corp\.?\s*off(?:ice)?"
            r"|head\s*office|factory|works|unit|plant|premises|complex|estate"
            r"|plot|sector|phase|block|lane|street|road|marg|nagar|puram|gali"
            r"|compound|industrial\s*(?:area|estate)?|gidc|midc|riico|sidco|kiadb|sez"
            r"|village|taluka|tehsil|dist(?:rict)?|city|state"
            r"|floor|tower|building|house|survey\s*no|khasra\s*no|post\s*box|p\.?o\.?"
            r"|india|delhi|new\s*delhi|mumbai|bombay|bengaluru|bangalore|chennai|madras|kolkata|calcutta"
            r"|hyderabad|pune|ahmedabad|surat|jaipur|lucknow|kanpur|nagpur|indore|thane|bhopal|patna"
            r"|vadodara|baroda|ghaziabad|ludhiana|agra|nashik|faridabad|meerut|rajkot|varanasi|amritsar"
            r"|navi\s*mumbai|prayagraj|howrah|ranchi|gwalior|jabalpur|coimbatore|vijayawada|jodhpur|madurai"
            r"|raipur|kota|chandigarh|guwahati|solan|baddi|haridwar|pantnagar|dehradun|gurugram|gurgaon"
            r"|noida|greater\s*noida|anand|vapi|ankleshwar|silvassa|daman|goa|kerala|tamil\s*nadu|karnataka"
            r"|andhra|telangana|maharashtra|gujarat|rajasthan|punjab|haryana|uttar\s*pradesh|madhya\s*pradesh"
            r"|west\s*bengal|bihar|odisha|assam|uttarakhand|himachal|uk|up|mp|hp|wb"
            r")\b",
            re.IGNORECASE
        )

        def normalize_kw(raw: str) -> str:
            r = raw.lower()
            if "manufactured" in r and "marketed" in r:
                return "Manufactured & Marketed By"
            if "packed" in r and "marketed" in r:
                return "Packed & Marketed By"
            if "imported" in r and "marketed" in r:
                return "Imported & Marketed By"
            if "mfg" in r or "manufac" in r:
                return "Manufactured By"
            if "pkd" in r or "pack" in r:
                return "Packed By"
            if "mkt" in r or "market" in r:
                return "Marketed By"
            if "import" in r:
                return "Imported By"
            return raw.title()

        entity_blocks = []

        # 1. Identify all manufacturer / packer / marketer declarations
        for idx, line in enumerate(lines):
            match = mfg_pattern.search(line)
            if match:
                raw_kw = match.group(1).strip()
                kw = normalize_kw(raw_kw)
                inline_content = match.group(2).strip()

                # Clean trailing other declarations from inline content
                clean_inline = other_decl_pattern.split(inline_content)[0].strip().rstrip(":,;-")

                entity_name = ""
                addr_start_idx = idx + 1

                if len(clean_inline) > 2:
                    entity_name = f"{kw}: {clean_inline}"
                elif idx + 1 < len(lines):
                    next_cand = lines[idx + 1].strip()
                    if not other_decl_pattern.search(next_cand) and not mfg_pattern.search(next_cand):
                        entity_name = f"{kw}: {next_cand}"
                        addr_start_idx = idx + 2
                    else:
                        entity_name = kw
                else:
                    entity_name = kw

                # Collect subsequent address lines for this entity (up to 10 lines to cover multi-line entity addresses)
                collected_address_lines = []
                for next_idx in range(addr_start_idx, min(addr_start_idx + 10, len(lines))):
                    cand = lines[next_idx].strip()
                    if not cand:
                        continue
                    # Boundary stop: another statutory declaration
                    if other_decl_pattern.search(cand):
                        break
                    # Boundary stop: another entity declaration
                    if mfg_pattern.search(cand):
                        break

                    has_pin = bool(pin_pattern.search(cand))
                    has_addr_kw = bool(address_keywords_pattern.search(cand))
                    looks_like_address = has_pin or has_addr_kw or ("," in cand and len(cand.split()) <= 12) or any(k in cand.lower() for k in ["road", "mumbai", "delhi", "worli", "lane", "street", "nagar", "floor", "plot", "building", "india", "maharashtra", "karnataka", "haryana"])

                    if looks_like_address:
                        cand_cleaned = other_decl_pattern.split(cand)[0].strip().rstrip(":,;-")
                        if cand_cleaned:
                            collected_address_lines.append(cand_cleaned)
                        if has_pin:
                            break

                addr_str = ", ".join(collected_address_lines)
                full_entity_str = f"{entity_name}, {addr_str}" if addr_str else entity_name

                entity_blocks.append({
                    "full_str": full_entity_str,
                    "has_pin": bool(pin_pattern.search(full_entity_str)),
                    "has_addr": bool(address_keywords_pattern.search(full_entity_str)) or len(collected_address_lines) > 0,
                    "kw": kw
                })

        if not entity_blocks:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value="Not detected",
                verdict=ComplianceVerdict.NON_COMPLIANT.value,
                reason="Mandatory declaration missing under Rule 6(1)(a): no manufacturer, packer, or importer identity detected.",
                rule_reference=rule_ref,
            )

        # 2. Combine entities or select the comprehensive declaration
        if len(entity_blocks) == 1:
            final_extracted = entity_blocks[0]["full_str"]
        else:
            final_extracted = " ; ".join(eb["full_str"] for eb in entity_blocks)

        # 3. If no PIN code in final_extracted yet, search for associated address blocks.
        #    This covers: a) scattered address blocks, b) Indian address under Customer Care /
        #    Marketed By when the primary MFG BY line only has a foreign entity name.
        if not pin_pattern.search(final_extracted):
            # Pattern: customer care / consumer care / marketed by / packed by / office blocks
            assoc_block_pattern = re.compile(
                r"\b(?:customer\s*care(?:\s*executive)?|consumer\s*care(?:\s*cell|\s*executive)?"
                r"|marketed\s*by|packed\s*by|pkd\.?\s*by|mkt\.?\s*by"
                r"|for\s*(?:feedback|complaint[s]?|queries)"
                r"|contact\s*(?:us|address|at)"
                r"|indian\s*(?:address|office)|regd\.?\s*(?:office|addr)"
                r")\b",
                re.IGNORECASE
            )
            for idx, line in enumerate(lines):
                line_clean = line.strip()
                # Skip lines that belong to prices, dates, licenses, or batch
                if re.search(r"\b(?:mrp|price|mfd\.?\s*date|mfg\.?\s*date|exp\.?\s*date|use\s*before|best\s*before|batch|lot|fssai|rc\s*no)\b", line_clean, re.IGNORECASE):
                    continue

                if pin_pattern.search(line_clean):
                    found_addr_parts = []
                    # Check preceding 1-3 lines for address premises or care/marketing header
                    for prev_idx in range(max(0, idx - 3), idx):
                        prev_line = lines[prev_idx].strip()
                        is_care_or_assoc = assoc_block_pattern.search(prev_line)
                        has_addr_kw = address_keywords_pattern.search(prev_line)
                        if (is_care_or_assoc or has_addr_kw) and not other_decl_pattern.search(prev_line):
                            prev_clean = other_decl_pattern.split(prev_line)[0].strip().rstrip(":,;-")
                            # Strip phone/email tokens if embedded
                            prev_clean = re.sub(r"\b(?:tel|phone|ph|email|e-mail)\s*[:\-].*", "", prev_clean, flags=re.IGNORECASE).strip().rstrip(":,;-")
                            if prev_clean and prev_clean not in found_addr_parts:
                                found_addr_parts.append(prev_clean)

                    pin_line_clean = other_decl_pattern.split(line_clean)[0].strip().rstrip(":,;-")
                    pin_line_clean = re.sub(r"\b(?:tel|phone|ph|email|e-mail)\s*[:\-].*", "", pin_line_clean, flags=re.IGNORECASE).strip().rstrip(":,;-")
                    if pin_line_clean and pin_line_clean not in found_addr_parts:
                        found_addr_parts.append(pin_line_clean)

                    if found_addr_parts and pin_pattern.search(", ".join(found_addr_parts)):
                        unattached_addr = ", ".join(found_addr_parts)
                        if unattached_addr.lower() not in final_extracted.lower():
                            final_extracted = f"{final_extracted} ; Associated Indian Address: {unattached_addr}"
                    break

        # 4. Strictly evaluate compliance and align justification with what is genuinely present in final_extracted
        pin_in_extracted = pin_pattern.search(final_extracted)
        has_pin = bool(pin_in_extracted)
        has_address = bool(address_keywords_pattern.search(final_extracted))

        if has_pin:
            pin_code = pin_in_extracted.group(0).strip()
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=final_extracted,
                verdict=ComplianceVerdict.COMPLIANT.value,
                reason=f"Manufacturer/packer identity with complete postal address and PIN code ({pin_code}) verified per Rule 6(1)(a).",
                rule_reference=rule_ref,
            )
        elif has_address:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=final_extracted,
                verdict=ComplianceVerdict.ADVISORY.value,
                reason="Manufacturer/packer name and premise address detected, but 6-digit postal PIN code is missing from the address per Rule 6(1)(a).",
                rule_reference=rule_ref,
            )
        else:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=final_extracted,
                verdict=ComplianceVerdict.ADVISORY.value,
                reason="Manufacturer/packer identity detected, but complete postal address / 6-digit PIN code is missing from the declaration.",
                rule_reference=rule_ref,
            )

    def _check_net_quantity(self, lines: List[str], full_text: str) -> FieldCompliance:
        """Rule 6(1)(b) & Rule 12: Net quantity in standard SI metric units."""
        field_id = "net_quantity"
        field_name = "Net Quantity Declaration"
        rule_ref = "Legal Metrology Rules 2011, Rule 6(1)(b) & Rule 12"

        # Explicit exclusions for nutrition table / portion declarations
        nutrition_exclusions = re.compile(
            r"\b("
            r"serving(?:\s*size)?"
            r"|per\s*serv(?:ing|e)?"
            r"|servings?\s*(?:per|in)"
            r"|portion(?:\s*size)?"
            r"|per\s*100\s*(?:g|gm|ml)"
            r"|nutrition(?:al)?"
            r"|nutrition\s*facts"
            r"|typical\s*values?"
            r"|energy"
            r"|calories"
            r"|protein"
            r"|carbohydrate[s]?"
            r"|net\s*carb(?:ohydrate)?[s]?"
            r"|cholesterol"
            r"|sodium"
            r"|added\s*sugar[s]?"
            r"|dietary\s*fiber"
            r")\b",
            re.IGNORECASE
        )

        qty_units_re = r"(?:kg|g|gm|gms|mg|ml|l|ltr|litre|litres|n|units?|pcs|pieces?)"
        qty_pattern = re.compile(
            rf"(\b\d+(?:\.\d+)?\s*{qty_units_re}\b(?:\s*\([^\)]+\))?)",
            re.IGNORECASE
        )

        # Statutory net prefixes: "Net Wt", "Net Weight", "Net Qty", "Net Quantity", "Net Vol", "Net Content(s)", "Net Mass", "Net", etc.
        prefix_pattern = re.compile(
            r"\b(?:net\s*(?:qty|quantity|wt|weight|vol|volume|content[s]?|mass|count)?|net(?:qty|quantity|wt|weight|vol|volume|contents?)|net)\b",
            re.IGNORECASE
        )

        # Regex for prefix + quantity directly on the same line
        # e.g., "Net Weight: 500 g", "NET WT. 1 kg (when packed)", "NET: 250 ml", "Net Qty 1 N"
        net_same_line_pattern = re.compile(
            rf"\b(?:net\s*(?:qty|quantity|wt|weight|vol|volume|content[s]?|mass|count)?|net(?:qty|quantity|wt|weight|vol|volume|contents?)|net)\s*[:\.\-]?\s*(\d+(?:\.\d+)?\s*{qty_units_re}\b(?:\s*\([^\)]+\))?)",
            re.IGNORECASE
        )

        # Regex for quantity followed by net suffix: e.g. "500 g Net", "1 kg Net Wt."
        net_postfix_pattern = re.compile(
            rf"(\b\d+(?:\.\d+)?\s*{qty_units_re}\b(?:\s*\([^\)]+\))?)\s*(?:net\s*(?:wt|weight|qty|quantity|content[s]?|mass)?|net)\b",
            re.IGNORECASE
        )

        found_candidates = []

        # 1. Search for genuine net quantity declarations
        for idx, line in enumerate(lines):
            if nutrition_exclusions.search(line):
                continue

            # Case A: Same-line net declaration (prefix before quantity)
            same_match = net_same_line_pattern.search(line)
            if same_match:
                found_candidates.append((same_match.group(1).strip(), True, 3))

            # Case B: Same-line net declaration (quantity before net suffix)
            postfix_match = net_postfix_pattern.search(line)
            if postfix_match:
                found_candidates.append((postfix_match.group(1).strip(), True, 3))

            # Case C: Multiline declaration where line idx has the prefix alone
            if prefix_pattern.search(line) and not re.search(r"\b(?:mrp|batch|lic)\b", line, re.IGNORECASE):
                for offset in [1, 2, 3]:
                    if idx + offset < len(lines):
                        next_line = lines[idx + offset].strip()
                        if nutrition_exclusions.search(next_line):
                            continue
                        next_match = qty_pattern.search(next_line)
                        if next_match:
                            found_candidates.append((next_match.group(1).strip(), True, 2))
                            break

            # Case D: Standalone prominent metric quantity (e.g. 100 g, 100ml)
            standalone_match = qty_pattern.search(line)
            if standalone_match and not any(k in line.lower() for k in ["per", "serving", "approx"]):
                found_candidates.append((standalone_match.group(1).strip(), False, 1))

        if found_candidates:
            # Prioritize declarations with official statutory prefix first
            found_candidates.sort(key=lambda x: x[2], reverse=True)
            found_qty, has_statutory_prefix, _ = found_candidates[0]
        else:
            found_qty, has_statutory_prefix = None, False

        if found_qty:
            clean_display = f"Net Qty: {found_qty}" if (has_statutory_prefix and not found_qty.lower().startswith("net")) else found_qty
            if has_statutory_prefix:
                return FieldCompliance(
                    field_id=field_id,
                    field_name=field_name,
                    extracted_value=clean_display,
                    verdict=ComplianceVerdict.COMPLIANT.value,
                    reason="Net quantity declared in standard metric units with statutory prefix per Rule 12.",
                    rule_reference=rule_ref,
                )
            else:
                return FieldCompliance(
                    field_id=field_id,
                    field_name=field_name,
                    extracted_value=clean_display,
                    verdict=ComplianceVerdict.ADVISORY.value,
                    reason="Metric quantity detected, but ensure statutory prefix 'Net Quantity' is prominently affixed per Rule 12.",
                    rule_reference=rule_ref,
                )

        return FieldCompliance(
            field_id=field_id,
            field_name=field_name,
            extracted_value="Not detected",
            verdict=ComplianceVerdict.NON_COMPLIANT.value,
            reason="Mandatory declaration missing under Rule 6(1)(b): no net quantity in standard metric units detected.",
            rule_reference=rule_ref,
        )

    def _check_mrp(self, lines: List[str], full_text: str) -> FieldCompliance:
        """Rule 6(1)(e): Maximum Retail Price with currency and 'inclusive of all taxes'."""
        field_id = "mrp_declaration"
        field_name = "Maximum Retail Price (MRP)"
        rule_ref = "Legal Metrology Rules 2011, Rule 6(1)(e)"

        # Lines containing registration codes, batch/lot/lic numbers must be excluded
        # from MRP parsing UNLESS they also carry an explicit MRP prefix.
        code_exclusion_pattern = re.compile(
            r"\b(?:rc\s*no|reg(?:istration)?\s*(?:cert(?:ificate)?)?\s*no|batch\s*no|lot\s*no"
            r"|b\.?\s*no|lic\s*no|fssai)\b",
            re.IGNORECASE
        )

        # Case A: Explicit MRP prefix followed by optional currency and price (handles "MRP2790", "MRP ₹2790/-", "M.R.P. Rs. 2790")
        mrp_strict_pattern = re.compile(
            r"\b(?:m\.?r\.?p\.?|maximum\s*retail\s*price|max\.?\s*retail\s*price)"
            r"\s*(?:is\s*)?[:\.\-]?\s*(?:rs\.?|inr|\u20b9)?\s*"
            r"([0-9]{1,6}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)\s*(?:/-)?",
            re.IGNORECASE
        )

        # Case B: Currency symbol before price, with MRP suffix in parentheses or immediately after
        symbol_first_pattern = re.compile(
            r"(?:rs\.?|inr|\u20b9)\s*([0-9]{1,6}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)\s*"
            r"(?:/-)?\s*(?:\([^\)]*m\.?r\.?p[^\)]*\)|\bm\.?r\.?p\.?\b)",
            re.IGNORECASE
        )

        found_price = None
        tax_in_mrp_line = False

        for idx, line in enumerate(lines):
            # Skip lines that are purely registration/batch codes without an explicit MRP prefix
            has_mrp_prefix = bool(re.search(r"\b(?:m\.?r\.?p\.?|maximum\s*retail\s*price)\b", line, re.IGNORECASE))
            if code_exclusion_pattern.search(line) and not has_mrp_prefix:
                continue

            # Case A: Strict same-line match
            match = mrp_strict_pattern.search(line)
            if match:
                found_price = match.group(1).replace(",", "")
                if any(k in line.lower() for k in ["tax", "taxes"]):
                    tax_in_mrp_line = True
                break

            # Case B: Currency symbol before price with trailing MRP label
            match_sym = symbol_first_pattern.search(line)
            if match_sym:
                found_price = match_sym.group(1).replace(",", "")
                if any(k in line.lower() for k in ["tax", "taxes"]):
                    tax_in_mrp_line = True
                break

            # Case C: MRP prefix alone on a line (price on next line)
            if has_mrp_prefix and not match:
                if any(k in line.lower() for k in ["tax", "taxes"]):
                    tax_in_mrp_line = True
                for offset in [1, 2]:
                    if idx + offset < len(lines):
                        next_line = lines[idx + offset].strip()
                        if code_exclusion_pattern.search(next_line):
                            continue
                        price_match = re.search(
                            r"(?:rs\.?|inr|\u20b9)?\s*([0-9]{1,6}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?)\s*(?:/-)?",
                            next_line, re.IGNORECASE
                        )
                        if price_match and price_match.group(1):
                            found_price = price_match.group(1).replace(",", "")
                            if any(k in next_line.lower() for k in ["tax", "taxes"]):
                                tax_in_mrp_line = True
                            break
                if found_price:
                    break

        if not found_price:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value="Not detected",
                verdict=ComplianceVerdict.NON_COMPLIANT.value,
                reason="Mandatory declaration missing under Rule 6(1)(e): no retail price (MRP) declaration detected.",
                rule_reference=rule_ref,
            )

        has_tax_clause = tax_in_mrp_line or bool(
            re.search(
                r"\b(?:incl\.?\s*(?:of\s*)?all\s*taxes|incl\.of\s*all\s*taxes|inclusive\s*of\s*all\s*taxes|incl\.?\s*taxes|all\s*taxes\s*incl)\b",
                full_text,
                re.IGNORECASE
            )
        )

        currency_str = "Rs."
        clean_mrp_value = f"{currency_str} {found_price}"
        if has_tax_clause:
            clean_mrp_value += " (incl. of all taxes)"

        if has_tax_clause:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=clean_mrp_value,
                verdict=ComplianceVerdict.COMPLIANT.value,
                reason="MRP declared with price and mandatory 'inclusive of all taxes' clause per Rule 6(1)(e).",
                rule_reference=rule_ref,
            )
        else:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=clean_mrp_value,
                verdict=ComplianceVerdict.ADVISORY.value,
                reason="MRP amount detected, but mandatory statutory statement 'inclusive of all taxes' is not clearly visible.",
                rule_reference=rule_ref,
            )

    def _check_mfg_date(self, lines: List[str], full_text: str) -> FieldCompliance:
        """Rule 6(1)(d): Month and year of manufacture or pre-packing."""
        field_id = "mfg_date"
        field_name = "Month & Year of Manufacture / Packing"
        rule_ref = "Legal Metrology Rules 2011, Rule 6(1)(d)"

        date_pattern_str = (
            r"(\b(?:0[1-9]|1[0-2])[/\-\.](?:20\d\d|\d\d)\b"
            r"|\b\d{1,2}[/\-\.]\d{1,2}[/\-\.](?:20\d\d|\d\d)\b"
            r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,\.\-]+(?:20\d\d|\d\d)\b)"
        )
        date_pattern = re.compile(date_pattern_str, re.IGNORECASE)

        # Lines with these triggers are EXPIRY declarations — never use as manufacture date
        expiry_pattern = re.compile(
            r"\b(?:use\s*before|use\s*by|expiry\s*date|expiry|exp\.?\s*date|exp\b|best\s*before)\b",
            re.IGNORECASE
        )

        # Only accept these explicit manufacture/packing triggers
        mfg_date_trigger = re.compile(
            r"\b("
            r"mfd\.?\s*date|mfd\b|mfg\.?\s*date|mfg\b"
            r"|date\s*of\s*(?:mfg|manufacture)|manufacturing\s*date"
            r"|pkd\.?\s*date|packed\s*on|date\s*of\s*(?:pack|packing)|packed\s*date"
            r"|month\s*(?:&|and)\s*year\s*of\s*(?:mfg|manufacture|pack|packing)"
            r")\b",
            re.IGNORECASE
        )

        extracted_date = None

        for idx, line in enumerate(lines):
            l_lower = line.lower()

            # Skip lines that only contain a "when packed" statement without a date
            if "when packed" in l_lower and not mfg_date_trigger.search(line):
                continue

            # Must match a manufacture/packing trigger
            if not mfg_date_trigger.search(line):
                continue

            # If this line also contains an expiry marker, extract date ONLY from
            # the portion that follows the mfg trigger, not from the expiry portion
            if expiry_pattern.search(line):
                inline_match = re.search(
                    rf"{mfg_date_trigger.pattern}\s*[:\.\-]?\s*{date_pattern_str}",
                    line, re.IGNORECASE
                )
                if inline_match:
                    extracted_date = f"Mfg Date: {inline_match.group(2).strip()}"
                    break
                # Could not isolate mfg date portion — skip this line
                continue

            # Normal case: no expiry on same line
            date_match = date_pattern.search(line)
            if date_match:
                extracted_date = f"Mfg Date: {date_match.group(1).strip()}"
                break

            # Mfg trigger is on this line but date is on next line
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].strip()
                if not expiry_pattern.search(next_line):
                    next_match = date_pattern.search(next_line)
                    if next_match:
                        extracted_date = f"Mfg Date: {next_match.group(1).strip()}"
                        break

        if extracted_date:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=extracted_date,
                verdict=ComplianceVerdict.COMPLIANT.value,
                reason="Month and year of manufacture/packing clearly declared per Rule 6(1)(d).",
                rule_reference=rule_ref,
            )

        return FieldCompliance(
            field_id=field_id,
            field_name=field_name,
            extracted_value="Not detected",
            verdict=ComplianceVerdict.NON_COMPLIANT.value,
            reason="Mandatory declaration missing under Rule 6(1)(d): no month and year of manufacture or packaging detected.",
            rule_reference=rule_ref,
        )

    def _check_consumer_care(self, lines: List[str], full_text: str) -> FieldCompliance:
        """Rule 6(1)(f): Consumer grievance redressal details (helpline, email, address)."""
        field_id = "consumer_care"
        field_name = "Consumer Care Grievance Redressal"
        rule_ref = "Legal Metrology Rules 2011, Rule 6(1)(f)"

        # Phone: toll-free, +91, STD landline, or 10-digit mobile.
        # Supports formats: "Tel: +91-124-4567890", "TEL: +91 (022) 28456789", "1800-222-333"
        phone_regex = re.compile(
            r"(?:(?:tel|telephone|phone|ph|call|mobile|mob|contact|helpline|toll[\s\-]*free"
            r"|customer\s*care|consumer\s*care)\.?\s*(?:no\.?)?\s*[:\-]?\s*)?"
            r"(\+?91[\-\s]?(?:\(?0?\d{1,4}\)?[\-\s]?)?\d{6,10}"
            r"|\(?0\d{2,4}\)?[\-\s]?\d{6,8}"
            r"|1800[\-\s]?[0-9]{3}[-\s]?[0-9]{3,4}"
            r"|\b\d{5}[\-\s]?\d{5}\b"
            r"|\b\d{10}\b)",
            re.IGNORECASE
        )

        # Email: handles standard email, spaces around '@' from OCR, and [at]/(at) obfuscations
        email_regex = re.compile(
            r"([a-zA-Z0-9._%+-]+(?:\s*@\s*|\s*\[at\]\s*|\s*\(at\)\s*)"
            r"[a-zA-Z0-9.-]+(?:\s*\.\s*|\s*dot\s*)[a-zA-Z]{2,})",
            re.IGNORECASE
        )

        # Phone regex with explicit preceding contact keywords (Tel, Phone, Helpline, Customer Care, Contact)
        labeled_phone_regex = re.compile(
            r"(?:(?:tel|telephone|phone|ph|call|mobile|mob|contact|helpline|toll[\s\-]*free"
            r"|customer\s*care|consumer\s*care)\.?\s*(?:no\.?)?\s*[:\-]?\s*)"
            r"(\+?91[\-\s]?(?:\(?0?\d{1,4}\)?[\-\s]?)?\d{6,10}"
            r"|\(?0\d{2,4}\)?[\-\s]?\d{6,8}"
            r"|1800[\-\s]?[0-9]{3}[-\s]?[0-9]{3,4}"
            r"|\b\d{5}[\-\s]?\d{5}\b"
            r"|\b\d{10}\b)",
            re.IGNORECASE
        )

        # General phone pattern (used only if no labeled phone found, strictly skipping EAN/barcode lines)
        general_phone_regex = re.compile(
            r"(\+?91[\-\s]?(?:\(?0?\d{1,4}\)?[\-\s]?)?\d{6,10}"
            r"|\(?0\d{2,4}\)?[\-\s]?\d{6,8}"
            r"|1800[\-\s]?[0-9]{3}[-\s]?[0-9]{3,4}"
            r"|\b\d{5}[\-\s]?\d{5}\b"
            r"|\b\d{10}\b)",
            re.IGNORECASE
        )

        # Pattern identifying barcode / EAN / regulatory code lines that must never be treated as phone numbers
        barcode_exclusion_pattern = re.compile(
            r"\b(?:ean|barcode|upc|gtin|rc\s*no|batch|lot|lic\s*no|fssai)\b",
            re.IGNORECASE
        )

        extracted_phone = None
        extracted_email = None

        # Pass 1: Scan for emails and explicitly labeled phone numbers (Tel:, Phone:, Helpline:, etc.)
        for line in lines:
            line_str = line.strip()

            if not extracted_email:
                e_match = email_regex.search(line_str)
                if e_match:
                    raw_email = e_match.group(1).strip()
                    clean_email = re.sub(r"\s+", "", raw_email)
                    clean_email = clean_email.replace("[at]", "@").replace("(at)", "@").replace("dot", ".")
                    extracted_email = clean_email

            if not extracted_phone and not barcode_exclusion_pattern.search(line_str):
                p_match = labeled_phone_regex.search(line_str)
                if p_match:
                    p_val = p_match.group(1).strip().rstrip(":,;.-/")
                    if len(p_val) >= 7 and not (len(p_val) == 6 and p_val.isdigit()) and not (len(p_val) == 14 and p_val.isdigit()) and not (len(p_val) == 13 and p_val.isdigit()):
                        extracted_phone = p_val

        # Pass 2: If phone not found via label, search non-barcode lines
        if not extracted_phone:
            for line in lines:
                line_str = line.strip()
                if barcode_exclusion_pattern.search(line_str):
                    continue
                p_match = general_phone_regex.search(line_str)
                if p_match:
                    p_val = p_match.group(1).strip().rstrip(":,;.-/")
                    # Discard 6-digit PINs, 13-digit EANs, and 14-digit FSSAI numbers
                    if len(p_val) >= 7 and not (len(p_val) == 6 and p_val.isdigit()) and not (len(p_val) == 13 and p_val.isdigit()) and not (len(p_val) == 14 and p_val.isdigit()):
                        extracted_phone = p_val
                        break

        # Fallback to full_text for email if missing
        if not extracted_email:
            e_match = email_regex.search(full_text)
            if e_match:
                raw_email = e_match.group(1).strip()
                clean_email = re.sub(r"\s+", "", raw_email)
                extracted_email = clean_email.replace("[at]", "@").replace("(at)", "@").replace("dot", ".")

        if extracted_phone and extracted_email:
            display_val = f"{extracted_phone} / {extracted_email}"
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=display_val,
                verdict=ComplianceVerdict.COMPLIANT.value,
                reason="Dual consumer grievance contact channels (telephonic helpline and email) verified per Rule 6(1)(f).",
                rule_reference=rule_ref,
            )
        elif extracted_phone or extracted_email:
            display_val = extracted_phone if extracted_phone else extracted_email
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=display_val,
                verdict=ComplianceVerdict.ADVISORY.value,
                reason="Single consumer contact channel detected; providing both telephone helpline and email address is recommended under Rule 6(1)(f).",
                rule_reference=rule_ref,
            )

        return FieldCompliance(
            field_id=field_id,
            field_name=field_name,
            extracted_value="Not detected",
            verdict=ComplianceVerdict.NON_COMPLIANT.value,
            reason="Mandatory declaration missing under Rule 6(1)(f): no consumer care redressal contact detected.",
            rule_reference=rule_ref,
        )

    def _check_fssai(self, lines: List[str], full_text: str, is_food_product: bool = True) -> FieldCompliance:
        """Food Safety & Standards (FSSAI) License Number check."""
        field_id = "fssai_license"
        field_name = "FSSAI License / Registration"
        rule_ref = "FSS Packaging & Labelling Regulations / DoCA Norms"

        fssai_match = re.search(r"\b[12]\d{13}\b", full_text)
        # Strictly check for FSSAI keyword rather than general factory "lic no"
        has_fssai_keyword = "fssai" in full_text

        if fssai_match:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value=f"FSSAI Lic. No. {fssai_match.group(0)}",
                verdict=ComplianceVerdict.COMPLIANT.value,
                reason="Valid 14-digit FSSAI statutory license number verified on packaged food commodity.",
                rule_reference=rule_ref,
            )
        elif has_fssai_keyword:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value="FSSAI reference identified",
                verdict=ComplianceVerdict.ADVISORY.value,
                reason="FSSAI reference detected; ensure the full 14-digit license number is clearly legible on primary display.",
                rule_reference=rule_ref,
            )
        else:
            return FieldCompliance(
                field_id=field_id,
                field_name=field_name,
                extracted_value="Not detected",
                verdict=ComplianceVerdict.ADVISORY.value,
                reason="Food commodity detected without an explicit 14-digit FSSAI license; recommend verifying FSSAI registration.",
                rule_reference=rule_ref,
            )


# Module singleton
_compliance_service: Optional[ComplianceService] = None

def get_compliance_service() -> ComplianceService:
    global _compliance_service
    if _compliance_service is None:
        _compliance_service = ComplianceService()
    return _compliance_service
