"""Datos semilla: creadores, fuentes RSS, algunos vídeos y microlecciones propias.

Los IDs de canal y vídeo se verifican automáticamente la primera vez que el
backend tiene acceso a internet (oEmbed de YouTube, sin clave): lo que no
exista se marca como roto y desaparece del feed.
"""

# (channel_id, nombre, categoría, idioma, credibilidad)
CREATORS = [
    # IA
    ("UCYO_jab_esuFRV4b17AJtAw", "3Blue1Brown", "ia", "en", 0.95),
    ("UCbfYPyITQ-7l4upoX8nvctg", "Two Minute Papers", "ia", "en", 0.85),
    ("UCXUPKJO5MZQN11PqgIvyuvQ", "Andrej Karpathy", "ia", "en", 0.97),
    ("UCy5znSnfMsDwaLlROnZ7Qbg", "Dot CSV", "ia", "es", 0.9),
    ("UCZHmQk67mSJgfCCTn7xBfew", "Yannic Kilcher", "ia", "en", 0.85),
    # Programación
    ("UCsBjURrPoezykLs9EqgamOA", "Fireship", "programacion", "en", 0.85),
    ("UCCezIgC97PvUuR4_gbFUs5g", "Corey Schafer", "programacion", "en", 0.9),
    ("UCxPD7bsocoAMq8Dj18kmGyQ", "MoureDev by Brais Moure", "programacion", "es", 0.85),
    ("UCX9NJ471o7Wie1DQe94RVIg", "Fazt", "programacion", "es", 0.8),
    ("UC8ENHE5xdFSwx71u3fDH5Xw", "ThePrimeagen", "programacion", "en", 0.75),
    ("UCXuqSBlHAE6Xw-yeJA0Tunw", "Linus Tech Tips", "programacion", "en", 0.75),
    # Ciberseguridad
    ("UC9x0AN7BWHpCDHSm9NiJFJQ", "NetworkChuck", "ciberseguridad", "en", 0.75),
    ("UClcE-kVhqyiHCcjYwcpfj9w", "LiveOverflow", "ciberseguridad", "en", 0.92),
    ("UCVeW9qkBjo3zosnqUbG7CFw", "John Hammond", "ciberseguridad", "en", 0.85),
    ("UC9-y-6csu5WGm29I7JiwpnA", "Computerphile", "ciberseguridad", "en", 0.92),
    ("UCNHWpNqiM8yOQcHXtsluD7Q", "S4vitar", "ciberseguridad", "es", 0.88),
    # Ciencia
    ("UCHnyfMqiRRG1u-2MsSQLbXA", "Veritasium", "ciencia", "en", 0.92),
    ("UCsXVk37bltHxD1rDPwtNM8Q", "Kurzgesagt – In a Nutshell", "ciencia", "en", 0.9),
    ("UCbdSYaPD-lr1kW27UJuk8Pw", "QuantumFracture", "ciencia", "es", 0.88),
    ("UCxzC4EngIsMrPmbm6Nxvb-A", "Scott Manley", "ciencia", "en", 0.88),
    ("UCLA_DiR1FfKNvjuUpBHmylQ", "NASA", "ciencia", "en", 0.97),
    ("UCY1kMZp36IQSyNx_9h4mpCg", "Mark Rober", "ciencia", "en", 0.82),
    ("UC6107grRI4m0o2-emgoDnAA", "SmarterEveryDay", "ciencia", "en", 0.9),
    # Mente
    ("UC7IcJI8PUf5Z3zKxnZvTBog", "The School of Life", "mente", "en", 0.82),
    ("UCvQECJukTDE2i6aCoMnS-Vg", "Big Think", "mente", "en", 0.8),
    ("UC2D2CMWXMOVWx7giW1n3LIg", "Andrew Huberman", "mente", "en", 0.8),
    # Deporte
    ("UC68TLK0mAEzUyHx5x5k-S1Q", "Jeff Nippard", "deporte", "en", 0.88),
    ("UCe0TLA0EsQbE-MjuHXevj2A", "ATHLEAN-X", "deporte", "en", 0.75),
    ("UCGYYNGmyhZ_kwBF_lqqXdAQ", "Tifo Football", "deporte", "en", 0.85),
]

# Creadores que la IA "propone" de entrada para que puedas aprobarlos o descartarlos.
SUGGESTED_CREATORS = [
    ("UCSHZKyawb77ixDdsGog4iWA", "Lex Fridman", "ia", "en", 0.8,
     "Entrevistas largas con investigadores de IA, ciencia y filosofía."),
    ("UCWN3xxRkmTPmbKwht9FuE5A", "Siraj Raval", "ia", "en", 0.4,
     "Aparece mucho en búsquedas de IA, pero su credibilidad es discutida: revísalo antes de aprobar."),
    ("UC4QZ_LsYcvcq7qOsOhpAX4A", "ColdFusion", "programacion", "en", 0.8,
     "Documentales de tecnología e historia de empresas, bien investigados."),
]

# (kind, nombre, url, categoría, idioma, credibilidad)
SOURCES = [
    ("rss", "Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "ia", "en", 0.85),
    ("rss", "Google AI Blog", "https://blog.google/technology/ai/rss/", "ia", "en", 0.85),
    ("rss", "MIT Technology Review – IA", "https://www.technologyreview.com/topic/artificial-intelligence/feed", "ia", "en", 0.88),
    ("rss", "The Hacker News", "https://feeds.feedburner.com/TheHackersNews", "ciberseguridad", "en", 0.8),
    ("rss", "BleepingComputer", "https://www.bleepingcomputer.com/feed/", "ciberseguridad", "en", 0.85),
    ("rss", "Krebs on Security", "https://krebsonsecurity.com/feed/", "ciberseguridad", "en", 0.92),
    ("rss", "Una al día (Hispasec)", "https://unaaldia.hispasec.com/feed", "ciberseguridad", "es", 0.88),
    ("rss", "GitHub Blog", "https://github.blog/feed/", "programacion", "en", 0.85),
    ("rss", "Hacker News – Best", "https://hnrss.org/best", "programacion", "en", 0.7),
    ("rss", "Xataka", "https://www.xataka.com/feedburner.xml", "programacion", "es", 0.72),
    ("rss", "Quanta Magazine", "https://www.quantamagazine.org/feed/", "ciencia", "en", 0.95),
    ("rss", "ScienceDaily", "https://www.sciencedaily.com/rss/top/science.xml", "ciencia", "en", 0.85),
    ("rss", "NASA News", "https://www.nasa.gov/news-release/feed/", "ciencia", "en", 0.97),
    ("rss", "Nature", "https://www.nature.com/nature.rss", "ciencia", "en", 0.97),
    ("rss", "Aeon", "https://aeon.co/feed.rss", "mente", "en", 0.88),
    ("rss", "Psyche", "https://psyche.co/feed", "mente", "en", 0.88),
    ("rss", "Daily Stoic", "https://dailystoic.com/feed/", "mente", "en", 0.7),
    ("rss", "Stronger By Science", "https://www.strongerbyscience.com/feed/", "deporte", "en", 0.92),
    ("rss", "SimpliFaster (velocidad)", "https://simplifaster.com/feed/", "deporte", "en", 0.85),
    ("rss", "ESPN Fútbol", "https://www.espn.com/espn/rss/soccer/news", "deporte", "en", 0.75),
]

# Vídeos conocidos para que el feed tenga contenido desde el primer arranque.
# (video_id, título, canal, categoría, subtema, formato, duración aprox. en segundos)
SEED_VIDEOS = [
    ("aircAruvnKk", "But what is a neural network? | Deep learning chapter 1", "3Blue1Brown", "ia", "investigacion-ia", "long", 1100),
    ("wjZofJX0v4M", "Transformers, the tech behind LLMs | Deep Learning Chapter 5", "3Blue1Brown", "ia", "modelos", "long", 1650),
    ("eMlx5fFNoYc", "Attention in transformers, step-by-step | Deep Learning Chapter 6", "3Blue1Brown", "ia", "modelos", "long", 1570),
    ("zjkBMFhNj_g", "[1hr Talk] Intro to Large Language Models", "Andrej Karpathy", "ia", "modelos", "long", 3600),
    ("kCc8FmEb1nY", "Let's build GPT: from scratch, in code, spelled out.", "Andrej Karpathy", "ia", "investigacion-ia", "long", 7000),
    ("x7X9w_GIm1s", "Python in 100 Seconds", "Fireship", "programacion", "python", "short", 140),
    ("5C_HPTJg5ek", "Rust in 100 Seconds", "Fireship", "programacion", "lenguajes", "short", 150),
    ("LKCVKw9CzFo", "100+ Linux Things you Need to Know", "Fireship", "ciberseguridad", "linux-redes", "long", 760),
    ("ciNHn38EyRc", "Running an SQL Injection Attack", "Computerphile", "ciberseguridad", "vulnerabilidades", "long", 1000),
    ("spUNpyF58BY", "But what is the Fourier Transform? A visual introduction.", "3Blue1Brown", "ciencia", "descubrimientos", "long", 1250),
    ("DxL2HoqLbyA", "The Most Misunderstood Concept in Physics", "Veritasium", "ciencia", "descubrimientos", "long", 1650),
    ("uxPdPpi5W4o", "Why are 96,000,000 Black Balls on This Reservoir?", "Veritasium", "ciencia", "inventos", "long", 900),
    ("e-P5IFTqB98", "Black Holes Explained – From Birth to Death", "Kurzgesagt – In a Nutshell", "ciencia", "espacio", "long", 360),
    ("xoxhDk-hwuo", "Package Thief vs. Glitter Bomb Trap", "Mark Rober", "ciencia", "inventos", "long", 680),
    ("h6fcK_fRYaI", "The Egg – A Short Story", "Kurzgesagt – In a Nutshell", "mente", "ideas", "long", 470),
    ("MBRqu0YOH14", "Optimistic Nihilism", "Kurzgesagt – In a Nutshell", "mente", "filosofia", "long", 400),
    ("n3Xv_g3g-mA", "Loneliness", "Kurzgesagt – In a Nutshell", "mente", "psicologia", "long", 590),
    ("QmOF0crdyRU", "Controlling Your Dopamine For Motivation, Focus & Satisfaction", "Andrew Huberman", "mente", "psicologia", "long", 8200),
    ("UF8uR6Z6KLc", "Steve Jobs' 2005 Stanford Commencement Address", "Stanford", "mente", "ideas", "long", 900),
    ("u4ZoJKF_VuA", "Start with why – how great leaders inspire action", "TEDx Talks", "mente", "autoconocimiento", "long", 1080),
    ("iCvmsMzlF7o", "The power of vulnerability", "TED", "mente", "emociones", "long", 1230),
]

# Microlecciones originales de MyFeed: contenido propio (no de terceros) que
# garantiza que siempre haya algo valioso que ver, incluso sin conexión.
# (id, categoría, subtema, título, cuerpo, puntos clave)
KNOWLEDGE_CARDS = [
    ("acel-primeros-pasos", "deporte", "velocidad", "La aceleración se gana en los 3 primeros pasos",
     "En fútbol sala casi nunca llegas a velocidad máxima: la pista es corta. Lo que decide jugadas es la aceleración en 0-5 m. "
     "Trabaja salidas con el cuerpo inclinado hacia delante, empuje potente contra el suelo y brazos rápidos.",
     ["Prioriza sprints de 5-10 m con descanso completo", "Inclina el cuerpo ~45° en la salida", "Calidad > cantidad: 6-10 repeticiones bastan"]),
    ("pliometria-basica", "deporte", "velocidad", "Pliometría: salta menos, pero mejor",
     "La pliometría entrena la capacidad del tendón y el músculo de devolver energía rápido. "
     "Saltos al cajón, saltos con contramovimiento y skipping son la base. El objetivo es el contacto corto con el suelo, no el cansancio.",
     ["2-3 sesiones por semana", "Aterriza en silencio: señal de buena técnica", "Para cuando baja la altura o la velocidad"]),
    ("hipertrofia-volumen", "deporte", "gimnasio", "Hipertrofia: lo que dice la evidencia",
     "Para ganar músculo importan sobre todo el volumen semanal (≈10-20 series por músculo), acercarse al fallo (0-3 repeticiones en reserva) "
     "y la sobrecarga progresiva. El rango de repeticiones es flexible: de 6 a 30 funciona si el esfuerzo es alto.",
     ["10-20 series por músculo a la semana", "Termina cerca del fallo", "Sube peso o repeticiones con el tiempo"]),
    ("proteina-diaria", "deporte", "nutricion", "¿Cuánta proteína necesitas?",
     "Para deportistas que buscan rendimiento y masa muscular, la evidencia apunta a 1,6-2,2 g de proteína por kg de peso al día, "
     "repartida en 3-5 comidas. La creatina monohidrato (3-5 g/día) es uno de los suplementos con más respaldo científico.",
     ["1,6-2,2 g/kg/día", "Reparte en 3-5 tomas", "Creatina: 3-5 g diarios, sin carga"]),
    ("isquios-nordicos", "deporte", "recuperacion", "Isquiotibiales: el ejercicio nórdico",
     "Las lesiones de isquiotibiales son de las más comunes en fútbol. El curl nórdico ha mostrado reducir notablemente su incidencia. "
     "Empieza con pocas repeticiones: genera agujetas fuertes al principio.",
     ["1-2 veces por semana", "Empieza con 2×5 y progresa", "Combínalo con sprints regulares"]),
    ("sueno-rendimiento", "deporte", "recuperacion", "Dormir también es entrenar",
     "Dormir menos de 7 horas se asocia con peor tiempo de reacción, más riesgo de lesión y peor recuperación. "
     "Horario constante, habitación oscura y fresca y evitar pantallas antes de dormir ayudan más que cualquier suplemento.",
     ["Apunta a 7-9 horas", "Mismo horario cada día", "Luz solar por la mañana"]),
    ("ciber-cia", "ciberseguridad", "investigacion-seg", "La tríada CIA",
     "Toda la seguridad informática gira alrededor de tres propiedades: Confidencialidad (solo quien debe lo ve), "
     "Integridad (nadie lo altera sin que se note) y Disponibilidad (funciona cuando se necesita). Cada ataque rompe al menos una.",
     ["Confidencialidad: cifrado, control de acceso", "Integridad: hashes, firmas", "Disponibilidad: redundancia, anti-DDoS"]),
    ("ciber-nmap", "ciberseguridad", "herramientas", "Nmap en 60 segundos",
     "Nmap descubre qué hosts y servicios hay en una red. `nmap -sV objetivo` detecta versiones de servicios; "
     "`-p-` escanea los 65.535 puertos. Úsalo solo en sistemas propios o con permiso: escanear sin autorización puede ser ilegal.",
     ["-sV detecta versiones", "-p- todos los puertos", "Solo con autorización"]),
    ("ciber-privesc", "ciberseguridad", "pentesting", "Escalada de privilegios en Linux: por dónde empezar",
     "Tras obtener acceso, el siguiente paso en un laboratorio es convertirse en root. Revisa `sudo -l`, binarios SUID (`find / -perm -4000`), "
     "tareas cron y permisos de escritura raros. GTFOBins documenta cómo abusar de binarios comunes.",
     ["sudo -l primero", "Busca binarios SUID", "Practica en Hack The Box o TryHackMe"]),
    ("ciber-cve", "ciberseguridad", "vulnerabilidades", "Cómo leer un CVE",
     "Un CVE es un identificador único de una vulnerabilidad pública. Su puntuación CVSS (0-10) estima la gravedad, "
     "pero lo importante es el contexto: ¿es explotable de forma remota?, ¿hay exploit público?, ¿está en el catálogo KEV de CISA?",
     ["CVSS no lo es todo", "Exploit público = parchea ya", "Consulta el catálogo KEV"]),
    ("ciber-redes-osi", "ciberseguridad", "linux-redes", "TCP vs UDP en una frase",
     "TCP garantiza que los datos llegan completos y en orden (web, SSH, correo); UDP sacrifica esa garantía por velocidad "
     "(DNS, streaming, juegos). El handshake de TCP (SYN, SYN-ACK, ACK) es la base de muchos escaneos.",
     ["TCP: fiable y ordenado", "UDP: rápido y sin conexión", "SYN scan = handshake a medias"]),
    ("ia-agente", "ia", "agentes", "¿Qué es un agente de IA?",
     "Un agente es un modelo de lenguaje que trabaja en bucle: piensa qué hacer, usa una herramienta (buscar, ejecutar código, leer archivos), "
     "observa el resultado y decide el siguiente paso hasta cumplir el objetivo. La clave no es el modelo solo, sino las herramientas y el contexto que recibe.",
     ["Bucle: pensar → actuar → observar", "Las herramientas definen lo que puede hacer", "Buen contexto = mejores decisiones"]),
    ("ia-tokens", "ia", "modelos", "Tokens: la unidad con la que piensa un LLM",
     "Los modelos no leen palabras sino tokens (trozos de palabras). En español, una palabra suele ocupar 1-2 tokens. "
     "El precio, la velocidad y el límite de contexto de un modelo se miden en tokens.",
     ["~1,5 tokens por palabra en español", "Contexto = memoria de trabajo", "Más tokens = más coste"]),
    ("ia-rag", "ia", "herramientas-ia", "RAG: darle tus documentos a la IA",
     "Retrieval-Augmented Generation consiste en buscar fragmentos relevantes de tus documentos y pasárselos al modelo junto a la pregunta. "
     "Así responde con información actual y propia sin reentrenarlo.",
     ["Buscar → adjuntar → responder", "Reduce invenciones", "No requiere entrenar modelos"]),
    ("ia-automatizar", "ia", "automatizacion", "Qué automatizar primero",
     "Las mejores automatizaciones son tareas frecuentes, repetitivas y con reglas claras: resumir correos, clasificar archivos, "
     "generar informes. Empieza por algo que hagas cada día y que te quite 10 minutos.",
     ["Frecuente + repetitivo + reglas claras", "Mide el tiempo ahorrado", "Revisa los resultados al principio"]),
    ("ia-prompt", "ia", "herramientas-ia", "Un buen prompt en 4 partes",
     "Contexto (quién eres y para qué), tarea (qué quieres exactamente), formato (cómo quieres la respuesta) y ejemplos. "
     "Pedir que la IA explique su razonamiento o que haga preguntas antes de responder mejora mucho los resultados.",
     ["Contexto · Tarea · Formato · Ejemplos", "Sé específico", "Itera sobre la respuesta"]),
    ("prog-python-comprehension", "programacion", "python", "Python: comprensiones de listas",
     "`[x * 2 for x in numeros if x > 0]` crea una lista nueva filtrando y transformando en una línea. "
     "Existen también para diccionarios `{k: v for ...}` y conjuntos. Úsalas cuando la lógica sea simple; si no, un bucle es más legible.",
     ["Filtra y transforma en una línea", "También dict y set", "Legibilidad primero"]),
    ("prog-git", "programacion", "opensource", "Git: los 5 comandos del día a día",
     "`git status` (qué cambió), `git add -p` (elegir cambios), `git commit -m` (guardar), `git pull --rebase` (traer cambios) y `git push` (subir). "
     "Haz commits pequeños con mensajes que expliquen el porqué.",
     ["Commits pequeños", "add -p para revisar", "El mensaje explica el porqué"]),
    ("prog-big-o", "programacion", "python", "Big O sin miedo",
     "Big O describe cómo crece el coste de un algoritmo con el tamaño de la entrada. Buscar en una lista es O(n); en un diccionario, O(1) de media. "
     "Elegir la estructura de datos correcta suele importar más que micro-optimizar.",
     ["Lista: búsqueda O(n)", "Dict/set: O(1) medio", "Estructura correcta > micro-optimizar"]),
    ("prog-emulacion", "programacion", "hardware", "¿Cómo funciona un emulador?",
     "Un emulador imita el hardware de otra máquina en software: lee cada instrucción de la CPU original y la traduce o interpreta. "
     "Los emuladores modernos usan recompilación dinámica (JIT) para traducir bloques enteros y ganar velocidad.",
     ["Imita CPU, memoria y gráficos", "Intérprete vs JIT", "La precisión cuesta rendimiento"]),
    ("prog-docker", "programacion", "lenguajes", "Docker en una idea",
     "Un contenedor empaqueta una app con todo lo que necesita para ejecutarse igual en cualquier máquina. "
     "Una imagen es la receta; un contenedor, la receta en marcha. Imágenes pequeñas (alpine, slim) arrancan antes y gastan menos.",
     ["Imagen = receta, contenedor = ejecución", "Funciona igual en todas partes", "Imágenes slim ahorran recursos"]),
    ("mente-estoicismo", "mente", "filosofia", "La dicotomía del control",
     "Epicteto enseñaba a separar lo que depende de ti (tus juicios, tus acciones) de lo que no (la opinión ajena, el resultado final). "
     "Poner tu energía solo en lo primero reduce la ansiedad y mejora las decisiones.",
     ["Controla tus acciones, no los resultados", "Las opiniones ajenas no dependen de ti", "Menos ansiedad, más foco"]),
    ("mente-dopamina", "mente", "psicologia", "Doomscrolling y dopamina",
     "Las apps de vídeo infinito usan recompensas variables: nunca sabes si el siguiente vídeo será bueno, y eso engancha como una tragaperras. "
     "Poner límites de tiempo y elegir conscientemente qué consumir devuelve el control. Justo para eso existe MyFeed.",
     ["Recompensa variable = enganche", "Límites de tiempo ayudan", "Consumo intencional"]),
    ("mente-sesgo-confirmacion", "mente", "psicologia", "Sesgo de confirmación",
     "Tendemos a buscar y recordar la información que confirma lo que ya creemos. Para combatirlo: busca activamente argumentos contrarios "
     "y pregúntate qué evidencia te haría cambiar de opinión.",
     ["Busca la mejor versión del argumento contrario", "¿Qué me haría cambiar de idea?", "Diversifica tus fuentes"]),
    ("mente-emociones-nombrar", "mente", "emociones", "Ponle nombre a lo que sientes",
     "Etiquetar una emoción con precisión (no solo 'mal', sino 'frustrado' o 'decepcionado') reduce su intensidad. "
     "Es una de las bases de la inteligencia emocional: reconocer, nombrar y luego decidir cómo responder.",
     ["Reconocer → nombrar → responder", "Precisión emocional", "Pausa antes de reaccionar"]),
    ("mente-habitos", "mente", "autoconocimiento", "Hábitos: hazlo ridículamente fácil",
     "Un hábito nuevo se instala mejor cuando empieza muy pequeño (2 minutos) y se ancla a algo que ya haces: 'después del café, leo una página'. "
     "La identidad importa: no 'quiero correr', sino 'soy alguien que entrena'.",
     ["Empieza con 2 minutos", "Ánclalo a una rutina", "Cambia la identidad, no solo la meta"]),
    ("ciencia-jwst", "ciencia", "espacio", "Por qué el James Webb ve en infrarrojo",
     "La luz de las galaxias más lejanas se ha estirado hacia el infrarrojo por la expansión del universo. "
     "Por eso el telescopio James Webb observa en infrarrojo y necesita estar muy frío, protegido por un parasol del tamaño de una cancha de tenis.",
     ["Corrimiento al rojo cosmológico", "Infrarrojo atraviesa el polvo", "Opera a unos -230 °C"]),
    ("ciencia-crispr", "ciencia", "descubrimientos", "CRISPR en 60 segundos",
     "CRISPR-Cas9 es una herramienta que permite cortar el ADN en un punto exacto, como unas tijeras guiadas por GPS. "
     "Se usa para investigar genes, crear cultivos más resistentes y ya existen terapias aprobadas para enfermedades de la sangre.",
     ["Corta ADN en un punto preciso", "Ya hay terapias aprobadas", "Debate ético sobre su uso"]),
    ("ciencia-fusion", "ciencia", "innovacion", "Fusión nuclear: la energía de las estrellas",
     "La fusión une núcleos ligeros y libera enormes cantidades de energía sin residuos de larga duración. "
     "El reto es mantener plasma a más de 100 millones de grados el tiempo suficiente para que dé más energía de la que consume.",
     ["Une núcleos, no los rompe", "Plasma a >100 millones °C", "El reto: ganancia neta sostenida"]),
    ("ciencia-metodo", "ciencia", "descubrimientos", "Cómo saber si un estudio es fiable",
     "Pregunta: ¿cuántos participantes tiene?, ¿hay grupo control?, ¿se publicó en una revista revisada por pares?, ¿otros lo han replicado? "
     "Un solo estudio rara vez es definitivo; los metaanálisis pesan más.",
     ["Tamaño de muestra", "Grupo control", "Replicación y metaanálisis"]),
]
