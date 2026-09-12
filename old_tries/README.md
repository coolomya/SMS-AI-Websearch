# Local Private Search Assistant (SearXNG + Ollama LLM + Flask API)

A completely self-hosted, privacy-focused search engine aggregator and abstractor. It intercepts user queries from your local network, searches multiple backends securely using **SearXNG**, passes the raw text context into a local **Ollama** model (`llama3.2:3b`), and returns a cleaned, continuous summary formatted perfectly for an SMS payload (< 150 words).

---

## 🏗️ Architecture Overview

1. **Android Client / Browser**: Requests a search via local IP `http://<YOUR_PC_IP>:5000/search?q=query`.
2. **Flask Backend (`server.py`)**: Manages routing, tracking network states, and file logging.
3. **SearXNG Engine (Docker)**: Securely pulls raw structural data from Google, Bing, and Wikipedia.
4. **Ollama LLM**: Extracts relevant metadata, drops marketing text, and generates a structured summary response.

---

## 🛠️ Prerequisites

Ensure your system has the following core tools installed:
* **Docker & Docker Compose** (For running SearXNG)
* **Python 3.8+**
* **Ollama App** (For hosting local AI models)

---

## 🚀 Setup & Startup Instructions

### 1. Initialize and Run SearXNG
Navigate to your cloned `searxng` repository and configure the settings profile:

```bash
cd searxng

# Create your environment file from the template
cp -i .env.example .env

# Generate a strong instance secret key
openssl rand -hex 32
```

Open `searxng/settings.yml` in a text editor. Ensure that the **JSON format output is allowed** and that your binding ports are open to the entire network:

```yaml
search:
    formats:
        - html
        - json  # Ensure this is uncommented or added
```

Open the `docker-compose.yml` file and check that ports map to all local interfaces (`0.0.0.0`):
```yaml
ports:
  - "0.0.0.0:8080:8080"
```

Boot up the containers in detached (background) mode:
```bash
docker compose up -d
```
Verify it is active by loading `http://localhost:8080` in your web browser.

### 2. Prepare Ollama
Make sure your local Ollama daemon is active and download the lightweight Llama 3.2 model:
```bash
ollama run llama3.2:3b
```
*(You can type something or hit `Ctrl + D` to exit the LLM CLI once the download finishes; the model stays in memory).*

### 3. Setup Python Backend Environment
Navigate to your application code folder, initialize your dependencies, and run the API server:

```bash
# Install required libraries
pip install flask requests ollama

# Launch the network listener server
python server.py
```

---

## 📱 Mobile Connection & Usage

To connect from your Android phone, make sure your phone and computer are on the **same Wi-Fi network**.

1. Find your computer's local IP address (`ipconfig` on Windows or `ifconfig`/`ip a` on Mac/Linux).
2. Open your Android browser and send a query format structure:
   ```text
   http://<YOUR_COMPUTERS_LOCAL_IP>:5000/search?q=what+does+imugi+mean
   ```

---

## 📝 Logging and Debugging

The application creates a live logger system in your app directory. You can find full structural output histories, processing connection timelines, client requests, and token tracking metrics inside:

* **File Name**: `search_assistant.log`

To watch logs print dynamically in real-time as your mobile phone triggers them, run:
```bash
# On Linux/Mac:
tail -f search_assistant.log
```
