import json
import re
import unicodedata
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Union, Any, Optional

logger = logging.getLogger(__name__)

class MultiCategoryScoreClassifier:
    def __init__(self, config_rules: Dict[str, Dict[str, float]], normalize_text: bool = True):
        """
        Inicializa el clasificador con múltiples categorías y puntajes independientes.
        :param config_rules: Diccionario con la forma { "Categoria": { "keyword": peso } }
        """
        logger.debug(f"Inicializando MultiCategoryScoreClassifier con {len(config_rules)} categorías.")
        self.normalize_text = normalize_text
        self.category_rules = {}
        self.compiled_patterns = {}
        
        for category, rules in config_rules.items():
            normalized_rules = {}
            for kw, score in rules.items():
                clean_kw = self._remove_accents(kw.lower()) if self.normalize_text else kw
                normalized_rules[clean_kw] = score
            
            self.category_rules[category] = normalized_rules
            
            if normalized_rules:
                pattern_str = r'\b(' + '|'.join(re.escape(kw) for kw in normalized_rules.keys()) + r')\b'
                flags = re.IGNORECASE if self.normalize_text else 0
                self.compiled_patterns[category] = re.compile(pattern_str, flags)
            else:
                self.compiled_patterns[category] = None

    @classmethod
    def from_json(cls, json_path: Union[str, Path], normalize_text: bool = True) -> 'MultiCategoryScoreClassifier':
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        return cls(config, normalize_text)

    @staticmethod
    def _remove_accents(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = unicodedata.normalize('NFD', text)
        return ''.join(c for c in text if unicodedata.category(c) != 'Mn')

    def evaluate_text(self, text: Optional[str]) -> Dict[str, Any]:
        """
        Evalúa el texto contra todas las categorías, suma los puntajes por separado 
        y determina la categoría predominante.
        """
        if not text or not isinstance(text, str) or not text.strip():
            return {
                "categoria_principal": "Sin Clasificar",
                "scores_por_categoria": {cat: 0 for cat in self.category_rules.keys()},
                "evidencia_detallada": {}
            }

        clean_text = self._remove_accents(text.lower()) if self.normalize_text else text
        
        scores_por_categoria = {}
        evidencia_detallada = {}

        for category, pattern in self.compiled_patterns.items():
            category_score = 0.0
            found_keywords = {}
            
            if pattern:
                matches = pattern.finditer(clean_text)
                for match in matches:
                    keyword = match.group(1)
                    score = self.category_rules[category].get(keyword, 0)
                    category_score += score
                    
                    if keyword in found_keywords:
                        found_keywords[keyword]["apariciones"] += 1
                        found_keywords[keyword]["subtotal"] += score
                    else:
                        found_keywords[keyword] = {"puntaje_unitario": score, "apariciones": 1, "subtotal": score}

            scores_por_categoria[category] = category_score
            if found_keywords:
                evidencia_detallada[category] = found_keywords

        # Determinar la categoría principal (la de mayor puntaje)
        categoria_principal = "Sin Clasificar"
        max_score = 0
        for cat, score in scores_por_categoria.items():
            if score > max_score:
                max_score = score
                categoria_principal = cat

        return {
            "categoria_principal": categoria_principal,
            "scores_por_categoria": scores_por_categoria,
            "evidencia_detallada": evidencia_detallada
        }

    def process_payload(self, data: List[Dict[str, Any]], text_key: str) -> List[Dict[str, Any]]:
        for item in data:
            texto = item.get(text_key, "")
            resultado = self.evaluate_text(texto)
            item["analisis_multiscore"] = resultado
        return data

def main():
    parser = argparse.ArgumentParser(description="Clasificador Multi-Categoría por Score.")
    parser.add_argument("frase", type=str, nargs="?", help="La frase a evaluar.")
    parser.add_argument("-c", "--config", type=str, default="config.json", help="Ruta al JSON.")
    parser.add_argument("-l", "--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format='%(levelname)s - %(message)s')

    ruta_config = Path(args.config)
    if not ruta_config.exists():
        logger.error(f"Falta {ruta_config}")
        exit(1)

    clasificador = MultiCategoryScoreClassifier.from_json(ruta_config)

    if args.frase:
        resultado = clasificador.evaluate_text(args.frase)
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
    else:
        print("Modo Demo. Analizando payload de cobranzas...")
        payload = [
            {"id": "CALL-001", "transcripcion": "No tengo plata estoy cesante, pero si consigo trabajo les pago el viernes."},
            {"id": "CALL-002", "transcripcion": "Son unos sinverguenzas, voy a poner un reclamo en la cmf y hablar con mi abogado."},
            {"id": "CALL-003", "transcripcion": "Alo? No, número equivocado, aquí no vive."}
        ]
        procesado = clasificador.process_payload(payload, text_key="transcripcion")
        print(json.dumps(procesado, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
