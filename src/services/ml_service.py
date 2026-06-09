from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

INSUFFICIENT = {"status": "insufficient_data", "message": "Se necesitan más datos para el análisis"}


def convert_numpy(obj):
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    return obj


def _minutes_since_created(tramite: dict) -> float:
    created = tramite.get("createdAt")
    if created is None:
        return float(tramite.get("elapsedMinutes") or tramite.get("durationMinutes") or 0)
    if isinstance(created, datetime):
        now = datetime.now(timezone.utc) if created.tzinfo else datetime.now()
        return max((now - created).total_seconds() / 60, 0)
    if isinstance(created, str):
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return max((now - created_dt).total_seconds() / 60, 0)
        except Exception:
            pass
    return float(tramite.get("elapsedMinutes") or tramite.get("durationMinutes") or 0)


class MLService:

    def detect_bottlenecks(self, submissions: list) -> list:
        if len(submissions) < 3:
            return [INSUFFICIENT]

        grouped = defaultdict(list)
        for s in submissions:
            node_id = s.get("nodeId")
            duration = s.get("durationMinutes")
            if node_id and duration is not None:
                grouped[node_id].append(float(duration))

        if not grouped:
            return [INSUFFICIENT]

        node_ids = list(grouped.keys())
        avg_durations = [np.mean(grouped[n]) for n in node_ids]

        X = np.array(avg_durations).reshape(-1, 1)
        model = IsolationForest(contamination=0.2, random_state=42)
        scores = model.fit_predict(X)
        raw_scores = model.decision_function(X)

        results = []
        for i, node_id in enumerate(node_ids):
            is_bottleneck = scores[i] == -1
            entry = {
                "nodeId": node_id,
                "avgDuration": round(avg_durations[i], 2),
                "isBottleneck": is_bottleneck,
                "anomalyScore": round(float(raw_scores[i]), 4),
                "recommendation": (
                    "Este nodo presenta tiempos de procesamiento anómalos. Revisar carga de trabajo."
                    if is_bottleneck
                    else "Nodo operando dentro de parámetros normales."
                ),
            }
            results.append(convert_numpy(entry))

        results.sort(key=lambda x: x["avgDuration"], reverse=True)
        return results

    def predict_completion_time(self, tramite_data: dict) -> dict:
        history = tramite_data.get("history", [])
        if len(history) < 3:
            return INSUFFICIENT

        durations = [float(h.get("durationMinutes", 0)) for h in history if h.get("durationMinutes")]
        if len(durations) < 3:
            return INSUFFICIENT

        X = np.arange(len(durations)).reshape(-1, 1)
        y = np.array(durations)

        model = LinearRegression()
        model.fit(X, y)

        predicted = max(float(model.predict([[len(durations)]])[0]), 0)
        confidence = max(0.0, min(1.0, float(model.score(X, y))))

        factors = []
        if model.coef_[0] > 0:
            factors.append("Tendencia creciente en tiempos de procesamiento")
        elif model.coef_[0] < 0:
            factors.append("Tendencia decreciente en tiempos de procesamiento")
        factors.append(f"Promedio histórico: {round(float(np.mean(durations)), 2)} minutos")

        return convert_numpy({
            "estimatedMinutes": round(predicted, 2),
            "confidence": round(confidence, 4),
            "factors": factors,
        })

    def detect_anomalies(self, tramites: list) -> list:
        if not tramites:
            return []

        items = [(t, _minutes_since_created(t)) for t in tramites]

        if len(items) < 3:
            results = []
            for tramite, minutes in items:
                is_anomalous = minutes > 1440
                results.append(convert_numpy({
                    "tramiteId": str(tramite.get("_id", "")),
                    "code": tramite.get("code", ""),
                    "minutesWaiting": round(minutes, 2),
                    "isAnomalous": is_anomalous,
                    "score": -1.0 if is_anomalous else 0.0,
                    "reason": (
                        "Trámite activo por más de 24 horas sin completarse."
                        if is_anomalous
                        else "Trámite dentro del tiempo normal."
                    ),
                }))
            return results

        durations = [m for _, m in items]
        X = np.array(durations).reshape(-1, 1)
        model = IsolationForest(n_estimators=10, contamination=0.3, random_state=42)
        predictions = model.fit_predict(X)
        scores = model.decision_function(X)

        results = []
        for i, (tramite, minutes) in enumerate(items):
            is_anomalous = predictions[i] == -1
            results.append(convert_numpy({
                "tramiteId": str(tramite.get("_id", "")),
                "code": tramite.get("code", ""),
                "minutesWaiting": round(minutes, 2),
                "isAnomalous": is_anomalous,
                "score": round(float(scores[i]), 4),
                "reason": (
                    "Tiempo de espera significativamente superior al promedio del grupo."
                    if is_anomalous
                    else "Trámite dentro del rango normal del grupo."
                ),
            }))
        return results

    def prioritize_tramites(self, tramites: list) -> list:
        if not tramites:
            return []

        scored = []

        if len(tramites) < 3:
            for tramite in tramites:
                minutes = _minutes_since_created(tramite)
                if minutes > 720:
                    level, score, reason = "ALTA", 1.0, "Trámite activo por más de 12 horas."
                elif minutes > 360:
                    level, score, reason = "MEDIA", 0.5, "Trámite activo entre 6 y 12 horas."
                else:
                    level, score, reason = "BAJA", 0.2, "Trámite dentro del tiempo esperado."
                t = dict(tramite)
                t["_id"] = str(t.get("_id", ""))
                t["priorityScore"] = score
                t["priorityLevel"] = level
                t["priorityReason"] = reason
                t["minutesWaiting"] = round(minutes, 2)
                scored.append(convert_numpy(t))
        else:
            durations = [_minutes_since_created(t) for t in tramites]
            max_duration = max(durations) if max(durations) > 0 else 1

            for i, tramite in enumerate(tramites):
                elapsed = durations[i]
                wait_score = elapsed / max_duration

                process_type = str(tramite.get("processType", "")).lower()
                type_score = 0.8 if "urgente" in process_type or "critico" in process_type else 0.4

                urgency_flags = tramite.get("urgencyFlags", [])
                urgency_score = min(len(urgency_flags) * 0.2, 1.0) if urgency_flags else 0.0

                priority = round(wait_score * 0.5 + type_score * 0.3 + urgency_score * 0.2, 4)

                reasons = []
                if wait_score > 0.7:
                    reasons.append("Alto tiempo de espera acumulado")
                if type_score > 0.5:
                    reasons.append("Tipo de proceso de alta prioridad")
                if urgency_score > 0:
                    reasons.append("Marcadores de urgencia detectados")
                if not reasons:
                    reasons.append("Prioridad estándar")

                if priority >= 0.7:
                    level = "ALTA"
                elif priority >= 0.4:
                    level = "MEDIA"
                else:
                    level = "BAJA"

                t = dict(tramite)
                t["_id"] = str(t.get("_id", ""))
                t["priorityScore"] = priority
                t["priorityLevel"] = level
                t["priorityReason"] = "; ".join(reasons)
                t["minutesWaiting"] = round(elapsed, 2)
                scored.append(convert_numpy(t))

        scored.sort(key=lambda x: x["priorityScore"], reverse=True)
        return scored

    # Palabras que aparecen en casi toda consulta y no aportan discriminación
    _ES_STOPWORDS = {
        "a", "al", "algo", "ante", "antes", "aquel", "aquella", "aquellas", "aquellos",
        "con", "contra", "cual", "cuando", "de", "del", "desde", "donde", "durante",
        "e", "el", "ella", "ellas", "ellos", "en", "entre", "era", "eres", "es", "esa",
        "esas", "ese", "eso", "esos", "esta", "este", "esto", "estos", "fue", "han",
        "hay", "he", "hemos", "i", "la", "las", "le", "les", "lo", "los", "me", "mi",
        "mis", "mucho", "muchos", "muy", "ni", "no", "nos", "nosotros", "nuestra",
        "nuestro", "o", "os", "otra", "otras", "otro", "otros", "para", "pero", "por",
        "porque", "que", "quien", "quienes", "se", "sin", "sobre", "son", "su", "sus",
        "te", "tiene", "tienen", "todo", "todos", "tu", "tus", "un", "una", "unas",
        "uno", "unos", "usted", "y", "ya", "yo",
        # Verbos de acción genéricos que aparecen en todas las consultas
        "quiero", "necesito", "deseo", "quisiera", "solicitar", "pedir", "hacer",
        "realizar", "iniciar", "tramitar", "obtener", "conseguir", "quisiera",
        "poder", "puede", "puedo", "favor", "como", "saber", "informacion",
    }

    def recommend_policy(self, client_description: str, available_processes: list) -> dict:
        if not available_processes:
            return INSUFFICIENT

        # Documento enriquecido: nombre repetido 3× para que pese más en TF-IDF
        documents = []
        for p in available_processes:
            name = str(p.get("name", "")).strip().lower()
            desc = str(p.get("description", "")).strip().lower()
            # El nombre del proceso es la señal más discriminativa
            enriched = f"{name} {name} {name} {desc}"
            documents.append(enriched)

        query = client_description.lower().strip()

        try:
            vectorizer = TfidfVectorizer(
                min_df=1,
                ngram_range=(1, 2),            # unigramas + bigramas
                stop_words=list(self._ES_STOPWORDS),
            )
            tfidf_matrix = vectorizer.fit_transform(documents + [query])
        except Exception:
            return INSUFFICIENT

        client_vec  = tfidf_matrix[-1]
        process_vecs = tfidf_matrix[:-1]
        tfidf_scores = cosine_similarity(client_vec, process_vecs)[0]

        # Puntuación de solapamiento de palabras clave (tokens significativos en la consulta)
        query_tokens = {
            w for w in query.split()
            if w not in self._ES_STOPWORDS and len(w) > 2
        }
        keyword_scores = []
        for p in available_processes:
            proc_text = (
                str(p.get("name", "")) + " " + str(p.get("description", ""))
            ).lower()
            proc_tokens = set(proc_text.split())
            if query_tokens:
                overlap = len(query_tokens & proc_tokens) / len(query_tokens)
            else:
                overlap = 0.0
            keyword_scores.append(overlap)

        # Puntuación final: 55% TF-IDF semántico + 45% solapamiento exacto de palabras clave
        final_scores = [
            0.55 * float(tfidf_scores[i]) + 0.45 * keyword_scores[i]
            for i in range(len(available_processes))
        ]

        best_idx    = int(np.argmax(final_scores))
        best_score  = final_scores[best_idx]
        best_tfidf  = float(tfidf_scores[best_idx])
        best_kw     = keyword_scores[best_idx]
        proc        = available_processes[best_idx]
        proc_name   = proc.get("name", str(best_idx))

        # Umbral mínimo: por debajo del 8% no hay suficiente señal
        if best_score < 0.08:
            return {
                "status": "insufficient_data",
                "message": (
                    "No encontré un trámite que coincida con tu descripción. "
                    "Intenta ser más específico, por ejemplo: "
                    "'solicitar nueva conexión de agua', 'reclamo por corte', 'pago de factura'."
                ),
            }

        # Construir texto de razón informativo
        parts = [f"similitud semántica {round(best_tfidf * 100, 1)}%"]
        if best_kw > 0:
            parts.append(f"palabras coincidentes {round(best_kw * 100, 0):.0f}%")
        reason = (
            f"El proceso '{proc_name}' es el más relacionado con tu consulta "
            f"({', '.join(parts)})."
        )

        return convert_numpy({
            "recommendedProcess": proc,
            "confidenceScore": round(best_score, 4),
            "reason": reason,
        })
