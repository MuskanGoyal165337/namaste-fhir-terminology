import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("ayush_emr.etl.fhir_generator")

DEFAULT_FHIR_CONFIG = {
    "namaste_system_uri": "http://namaste.ayush.gov.in",
    "namaste_publisher": "Ministry of AYUSH, Government of India",
    "icd11_tm2_system_uri": "http://id.who.int/icd/release/11/mms",
    "icd11_tm2_publisher": "World Health Organization (WHO)",
    "conceptmap_uri": "http://namaste.ayush.gov.in/fhir/ConceptMap/namaste-to-icd11-tm2",
    "version": "1.0.0"
}

class FHIRGenerator:
    """
    Generates standard FHIR R4 CodeSystem and ConceptMap resources for AYUSH terminology.
    Ensures strict adherence to source semantics without fabricating non-existent codes.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**DEFAULT_FHIR_CONFIG, **(config or {})}

    def generate_namaste_codesystem(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates FHIR R4 CodeSystem resource for NAMASTE AYUSH concepts.
        Only includes concepts where a genuine code or valid source term exists.
        Does NOT claim tm2_code as a NAMASTE code.
        Preserves mapping_status and source_version from record provenance.
        """
        concepts = []
        for r in records:
            source_term = r.get("source_term") or r.get("term")
            display_name = r.get("display_name") or r.get("english") or source_term
            namaste_code = r.get("code") or source_term

            if not namaste_code:
                continue

            concept_def: Dict[str, Any] = {
                "code": str(namaste_code),
                "display": str(display_name)
            }
            if source_term and source_term != display_name:
                concept_def["definition"] = f"Original Term: {source_term}"

            props: List[Dict[str, Any]] = []
            if r.get("system"):
                props.append({"code": "system_category", "valueString": str(r["system"])})
            if r.get("tm2_code"):
                props.append({"code": "tm2_code", "valueString": str(r["tm2_code"])})
                if r.get("tm2_display"):
                    props.append({"code": "tm2_display", "valueString": str(r["tm2_display"])})
            if r.get("mapping_status"):
                props.append({"code": "mapping_status", "valueString": str(r["mapping_status"])})
            if r.get("source_version"):
                props.append({"code": "source_version", "valueString": str(r["source_version"])})
            if props:
                concept_def["property"] = props

            concepts.append(concept_def)

        codesystem = {
            "resourceType": "CodeSystem",
            "id": "codesystem-namaste-ayush",
            "url": self.config["namaste_system_uri"],
            "version": self.config["version"],
            "name": "NAMASTEAYUSHTerminology",
            "title": "NAMASTE AYUSH Terminology CodeSystem",
            "status": "active",
            "experimental": False,
            "date": datetime.now(timezone.utc).isoformat(),
            "publisher": self.config["namaste_publisher"],
            "content": "complete",
            "count": len(concepts),
            "property": [
                {"code": "system_category", "type": "string"},
                {"code": "tm2_code", "type": "string"},
                {"code": "tm2_display", "type": "string"},
                {"code": "mapping_status", "type": "string"},
                {"code": "source_version", "type": "string"},
            ],
            "concept": concepts
        }
        return codesystem


    def generate_icd11_tm2_codesystem(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates FHIR R4 CodeSystem resource for ICD-11 Traditional Medicine 2 (TM2) chapter.
        """
        unique_tm2_codes = {}
        for r in records:
            tm2_code = r.get("tm2_code")
            if tm2_code and tm2_code not in unique_tm2_codes:
                display = f"ICD-11 TM2 Category {tm2_code}"
                unique_tm2_codes[tm2_code] = {
                    "code": str(tm2_code),
                    "display": display
                }

        concepts = list(unique_tm2_codes.values())

        codesystem = {
            "resourceType": "CodeSystem",
            "id": "codesystem-icd11-tm2",
            "url": self.config["icd11_tm2_system_uri"],
            "version": self.config["version"],
            "name": "ICD11TM2Terminology",
            "title": "WHO ICD-11 Traditional Medicine Module 2 CodeSystem",
            "status": "active",
            "experimental": False,
            "date": datetime.now(timezone.utc).isoformat(),
            "publisher": self.config["icd11_tm2_publisher"],
            "content": "fragment",
            "count": len(concepts),
            "concept": concepts
        }
        return codesystem

    def generate_namaste_tm2_conceptmap(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generates FHIR R4 ConceptMap resource mapping NAMASTE concepts to ICD-11-TM2 concepts.
        Preserves exact source term and target tm2_code pairings.
        """
        map_elements = []
        for r in records:
            source_term = r.get("source_term") or r.get("term")
            namaste_code = r.get("code") or source_term
            tm2_code = r.get("tm2_code")
            display_name = r.get("display_name") or r.get("english") or source_term

            if not namaste_code or not tm2_code:
                continue

            element = {
                "code": str(namaste_code),
                "display": str(display_name),
                "target": [
                    {
                        "code": str(tm2_code),
                        "display": f"ICD-11 TM2 Code {tm2_code}",
                        "equivalence": "equivalent"
                    }
                ]
            }
            map_elements.append(element)

        conceptmap = {
            "resourceType": "ConceptMap",
            "id": "conceptmap-namaste-to-icd11-tm2",
            "url": self.config["conceptmap_uri"],
            "version": self.config["version"],
            "name": "NAMASTEToICD11TM2Map",
            "title": "NAMASTE AYUSH Terminology to WHO ICD-11-TM2 ConceptMap",
            "status": "active",
            "experimental": False,
            "date": datetime.now(timezone.utc).isoformat(),
            "publisher": self.config["namaste_publisher"],
            "sourceUri": self.config["namaste_system_uri"],
            "targetUri": self.config["icd11_tm2_system_uri"],
            "group": [
                {
                    "source": self.config["namaste_system_uri"],
                    "target": self.config["icd11_tm2_system_uri"],
                    "element": map_elements
                }
            ]
        }
        return conceptmap

    def export_fhir_resources(
        self,
        records: List[Dict[str, Any]],
        output_dir: str
    ) -> Dict[str, str]:
        """
        Exports all 3 FHIR JSON resources to processed output directory.
        """
        os.makedirs(output_dir, exist_ok=True)

        namaste_cs = self.generate_namaste_codesystem(records)
        icd11_cs = self.generate_icd11_tm2_codesystem(records)
        conceptmap = self.generate_namaste_tm2_conceptmap(records)

        paths = {
            "codesystem_namaste": os.path.join(output_dir, "codesystem_namaste.json"),
            "codesystem_icd11_tm2": os.path.join(output_dir, "codesystem_icd11_tm2.json"),
            "conceptmap_namaste_tm2": os.path.join(output_dir, "conceptmap_namaste_tm2.json")
        }

        with open(paths["codesystem_namaste"], "w", encoding="utf-8") as f:
            json.dump(namaste_cs, f, indent=4, ensure_ascii=False)

        with open(paths["codesystem_icd11_tm2"], "w", encoding="utf-8") as f:
            json.dump(icd11_cs, f, indent=4, ensure_ascii=False)

        with open(paths["conceptmap_namaste_tm2"], "w", encoding="utf-8") as f:
            json.dump(conceptmap, f, indent=4, ensure_ascii=False)

        logger.info(f"Generated FHIR resources successfully in {output_dir}")
        return paths
