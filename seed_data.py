import random
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "workflow_platform"

BOLIVIAN_NAMES = [
    ("Juan", "Mamani"), ("Maria", "Flores"), ("Carlos", "Quispe"), ("Ana", "Torrez"),
    ("Pedro", "Condori"), ("Rosa", "Limachi"), ("Luis", "Vargas"), ("Carmen", "Mamani"),
    ("Jorge", "Chavez"), ("Silvia", "Morales"), ("Antonio", "Huanca"), ("Elena", "Ticona"),
    ("Roberto", "Apaza"), ("Patricia", "Cruz"), ("Miguel", "Calisaya"), ("Laura", "Mendoza"),
    ("Fernando", "Quisbert"), ("Isabel", "Poma"), ("Raul", "Sullca"), ("Beatriz", "Colque"),
    ("Alejandro", "Mamani"), ("Cristina", "Huarachi"), ("Hugo", "Nina"), ("Sandra", "Yujra"),
    ("Gonzalo", "Chura"), ("Veronica", "Alanoca"), ("Freddy", "Quispe"), ("Natalia", "Ticona"),
    ("Marcos", "Flores"), ("Lorena", "Condori"), ("David", "Guarachi"), ("Sofia", "Villca"),
]

FORM_TEMPLATES = {
    "atencion": lambda nombre, ci: {
        "nombre_del_cliente": nombre,
        "ci": ci,
        "motivo_consulta": random.choice(["Nuevo servicio", "Reclamo", "Consulta tecnica", "Actualizacion de datos"]),
        "telefono_contacto": f"7{random.randint(1000000, 9999999)}",
        "descripcion": random.choice([
            "Cliente solicita instalacion de medidor",
            "Cliente reporta problemas con facturacion",
            "Solicitud de reconexion de servicio",
            "Reclamo por cobro incorrecto",
        ]),
    },
    "revision_tecnica": lambda nombre, ci: {
        "tecnico_asignado": random.choice(["Ing. Lopez", "Ing. Ramos", "Ing. Garcia", "Ing. Mamani"]),
        "resultado_inspeccion": random.choice(["Aprobado", "Observaciones menores", "Requiere revision"]),
        "observaciones": random.choice(["Sin observaciones", "Revisar tuberia principal", "Medidor en mal estado", "Instalacion correcta"]),
    },
    "resolucion": lambda nombre, ci: {
        "resolucion": random.choice(["Reclamo procedente", "Reclamo improcedente", "Solucion parcial"]),
        "accion_tomada": random.choice(["Ajuste en factura", "Reparacion realizada", "Visita tecnica programada"]),
        "fecha_resolucion": datetime.now().strftime("%d/%m/%Y"),
    },
    "documental": lambda nombre, ci: {
        "documentos_recibidos": random.choice(["Completos", "Incompletos", "Con observaciones"]),
        "estado_documentacion": random.choice(["Aprobado", "Pendiente de subsanacion"]),
        "observaciones": random.choice(["Documentacion en orden", "Falta carnet de identidad", "Falta plano de ubicacion"]),
    },
    "inspeccion": lambda nombre, ci: {
        "resultado": random.choice(["Apto para instalacion", "Requiere adecuaciones", "No apto temporalmente"]),
        "distancia_red": f"{random.randint(5, 150)} metros",
        "observaciones_tecnicas": random.choice(["Zona accesible", "Terreno rocoso", "Instalacion estandar"]),
    },
    "materiales": lambda nombre, ci: {
        "materiales_solicitados": random.choice(["Tuberia 1/2", "Medidor clase B", "Accesorios completos", "Kit de conexion"]),
        "cantidad": str(random.randint(1, 10)),
        "estado": random.choice(["Listo para instalacion", "En bodega", "Solicitado a proveedor"]),
    },
    "presupuesto": lambda nombre, ci: {
        "monto_total": f"Bs. {random.randint(500, 3000)}.00",
        "incluye_materiales": "Si",
        "vigencia": "30 dias",
        "numero_presupuesto": f"PRES-{random.randint(1000, 9999)}",
    },
    "pago": lambda nombre, ci: {
        "numero_recibo": f"REC-{random.randint(10000, 99999)}",
        "monto_pagado": f"Bs. {random.randint(500, 3000)}.00",
        "forma_pago": random.choice(["Efectivo", "Transferencia bancaria", "QR", "Deposito bancario"]),
    },
    "instalacion": lambda nombre, ci: {
        "tecnico_instalador": random.choice(["Tec. Mamani", "Tec. Quispe", "Tec. Flores", "Tec. Condori"]),
        "resultado": "Instalacion completada satisfactoriamente",
        "numero_medidor_instalado": f"MED-{random.randint(100000, 999999)}",
    },
    "activacion": lambda nombre, ci: {
        "numero_medidor": f"MED-{random.randint(100000, 999999)}",
        "lectura_inicial": "0000",
        "fecha_activacion": datetime.now().strftime("%d/%m/%Y"),
        "tipo_servicio": "Agua potable residencial",
    },
}


def get_form_data(node_label: str, nombre: str, ci: str) -> dict:
    label = node_label.lower()
    if "atencion" in label:
        return FORM_TEMPLATES["atencion"](nombre, ci)
    elif "revision tecnica" in label or "tecnica" in label:
        return FORM_TEMPLATES["revision_tecnica"](nombre, ci)
    elif "resolucion" in label or "reclamo" in label:
        return FORM_TEMPLATES["resolucion"](nombre, ci)
    elif "documental" in label or "documento" in label:
        return FORM_TEMPLATES["documental"](nombre, ci)
    elif "inspeccion" in label:
        return FORM_TEMPLATES["inspeccion"](nombre, ci)
    elif "material" in label:
        return FORM_TEMPLATES["materiales"](nombre, ci)
    elif "presupuesto" in label or "generar" in label:
        return FORM_TEMPLATES["presupuesto"](nombre, ci)
    elif "pago" in label or "registro" in label:
        return FORM_TEMPLATES["pago"](nombre, ci)
    elif "instalacion" in label:
        return FORM_TEMPLATES["instalacion"](nombre, ci)
    elif "activacion" in label or "servicio" in label:
        return FORM_TEMPLATES["activacion"](nombre, ci)
    return {"datos": "completado", "cliente": nombre}


def random_date_2026() -> datetime:
    start = datetime(2026, 1, 1, 8, 0, 0)
    end = datetime(2026, 6, 10, 18, 0, 0)
    delta = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta))


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    processes = list(db.processes.find({}, {"_id": 1, "name": 1, "nodes": 1}))
    if not processes:
        print("ERROR: No se encontraron procesos en MongoDB.")
        print("Verifica que la base de datos 'workflow_platform' existe y tiene datos.")
        client.close()
        return

    print(f"Encontrados {len(processes)} procesos:")
    process_data = []
    for p in processes:
        task_nodes = [n for n in p.get("nodes", []) if n.get("type") == "USER_TASK"]
        print(f"  [{p['_id']}] {p.get('name', '?')} — {len(task_nodes)} nodos de tarea")
        if task_nodes:
            process_data.append({
                "id": str(p["_id"]),
                "name": p.get("name", "Proceso"),
                "task_nodes": task_nodes,
            })

    if not process_data:
        print("ERROR: Ningun proceso tiene nodos de tipo USER_TASK.")
        client.close()
        return

    user_id = "69e8ce6aae8a16d15f0c2de1"
    num_tramites = 60

    statuses = (["COMPLETED"] * 42) + (["ACTIVE"] * 18)
    random.shuffle(statuses)

    names_pool = (BOLIVIAN_NAMES * 3)[:num_tramites]
    random.shuffle(names_pool)

    proc_assignments = [process_data[i % len(process_data)] for i in range(num_tramites)]
    random.shuffle(proc_assignments)

    tramites_to_insert = []
    submissions_to_insert = []

    for i in range(num_tramites):
        proc = proc_assignments[i]
        status = statuses[i]
        first_name, last_name = names_pool[i]
        full_name = f"{first_name} {last_name}".lower()
        ci = str(random.randint(1000000, 9999999))
        code = f"TRAM-SEED-{1000 + i}"
        tram_id = ObjectId()
        created_at = random_date_2026()
        task_nodes = proc["task_nodes"]

        if status == "COMPLETED":
            completed_count = len(task_nodes)
        else:
            completed_count = random.randint(0, max(0, len(task_nodes) - 1))

        history = [{
            "action": f"Tramite creado en nodo: {task_nodes[0]['label']}",
            "timestamp": created_at + timedelta(seconds=1),
        }]

        current_time = created_at + timedelta(minutes=random.randint(1, 30))
        current_node_id = task_nodes[0]["_id"]

        for j in range(completed_count):
            node = task_nodes[j]

            # 15% chance of anomalously slow node to feed ML models
            if random.random() < 0.15:
                duration = random.randint(300, 600)
            else:
                duration = random.randint(2, 120)

            node_start = current_time
            node_end = current_time + timedelta(minutes=duration)

            history.append({
                "action": f"Tarea completada en nodo: {node['label']} | Duracion: {duration} min",
                "timestamp": node_end,
            })

            submissions_to_insert.append({
                "_id": ObjectId(),
                "tramiteId": str(tram_id),
                "processId": proc["id"],
                "nodeId": node["_id"],
                "userId": user_id,
                "departmentId": node.get("departmentId", ""),
                "formData": get_form_data(node["label"], full_name, ci),
                "comments": random.choice(["", "Sin observaciones", "Revisado correctamente", "Documentacion completa"]),
                "startedAt": node_start,
                "submittedAt": node_end,
                "completedAt": node_end,
                "durationMinutes": duration,
                "createdAt": node_start,
                "updatedAt": node_end,
                "_class": "com.workflow.workflowplatform.model.TaskSubmission",
            })

            current_time = node_end + timedelta(minutes=random.randint(1, 60))
            if j + 1 < len(task_nodes):
                current_node_id = task_nodes[j + 1]["_id"]

        if status == "COMPLETED":
            current_node_id = task_nodes[-1]["_id"]

        tramites_to_insert.append({
            "_id": tram_id,
            "code": code,
            "processId": proc["id"],
            "userId": user_id,
            "clienteInfo": {
                "nombre": full_name,
                "ci": ci,
                "telefono": f"7{random.randint(1000000, 9999999)}",
                "email": f"{first_name.lower()}.{last_name.lower()}@gmail.com",
                "direccion": random.choice([
                    "Av. Cristo Redentor 123", "Calle Suarez Arana 45",
                    "Barrio Equipetrol Norte", "Av. San Martin 678",
                    "Zona Norte Km 5", "Av. Banzer 2do anillo",
                    "Barrio Las Palmas Mz 14", "Calle Cochabamba 890",
                ]),
            },
            "createdBy": user_id,
            "currentNodeId": current_node_id,
            "status": status,
            "history": history,
            "createdAt": created_at,
            "updatedAt": current_time,
            "_class": "com.workflow.workflowplatform.model.Tramite",
        })

    result_t = db.tramites.insert_many(tramites_to_insert)
    result_s = db.task_submissions.insert_many(submissions_to_insert) if submissions_to_insert else None

    completed = sum(1 for t in tramites_to_insert if t["status"] == "COMPLETED")
    active = sum(1 for t in tramites_to_insert if t["status"] == "ACTIVE")

    print(f"\nInsertados {len(result_t.inserted_ids)} tramites")
    print(f"Insertadas {len(result_s.inserted_ids) if result_s else 0} task_submissions")
    print(f"\nResumen:")
    print(f"  COMPLETED : {completed}")
    print(f"  ACTIVE    : {active}")
    print(f"  Submissions: {len(submissions_to_insert)}")
    print("\nSeed completado exitosamente.")
    client.close()


if __name__ == "__main__":
    random.seed(42)
    main()
