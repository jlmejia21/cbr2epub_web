# CBR/CBZ a EPUB - Web Application

Convertidor de archivos CBR/CBZ a formato EPUB optimizado para Kindle e iPad.

## Caracteristicas

- Conversion de archivos CBR/CBZ a EPUB
- Optimizacion automatica de imagenes
- Soporte para metadatos (titulo, autor)
- Interface web moderna con progreso en tiempo real
- Procesamiento en segundo plano

## Estructura del Proyecto

```
cbr2epub_web/
├── app.py              # Aplicacion Flask principal
├── requirements.txt    # Dependencias Python
├── templates/
│   └── index.html      # Interface web
└── lib/
    ├── extractor.py     # Extraccion de archivos CBR/CBZ
    ├── image_proc.py    # Procesamiento y optimizacion de imagenes
    ├── epub_builder.py  # Construccion del archivo EPUB
    ├── ai_upscale.py    # Escalado AI de imagenes
    ├── utils.py         # Utilidades
    └── models/          # Modelos AI (vacio, reservado para futuro)
```

## Requisitos

- Python 3.9+
- Flask 2.3+
- Pillow 10.0+
- gunicorn 21.0+
- rarfile 4.0+

## Instalacion Local

```bash
cd cbr2epub_web
pip install -r requirements.txt
python3 app.py
# Abrir http://localhost:5000
```

## API Endpoints

| Endpoint | Metodo | Descripcion |
|----------|--------|-------------|
| `/` | GET | Pagina principal |
| `/api/upload` | POST | Subir archivo e iniciar conversion |
| `/api/status/<task_id>` | GET | Ver estado de la conversion |
| `/api/download/<task_id>` | GET | Descargar EPUB completado |
| `/api/cleanup` | POST | Limpiar archivos antiguos |

## Licencia

MIT
