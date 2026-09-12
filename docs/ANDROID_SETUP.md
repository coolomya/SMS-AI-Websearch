Absolutely. I’d make the Android README a **standalone deployment guide**, while keeping it focused specifically on the Automate/SIM bridge.

# 📱 Android SMS-to-REST API Bridge

An efficient, lightweight Android SMS gateway for **SMS-AI-Websearch**.

The Android device uses **Automate by LlamaLab** to monitor incoming SMS messages, forward the message text to the local FastAPI backend over the same LAN, and send the AI-generated response back to the original sender via SMS.

This setup uses a physical Android phone with an active SIM card and SMS service. No native Android application code is required.

---

## 🏛️ Architecture

```text
┌──────────────────────┐
│   Designated Sender  │
│                      │
│      SMS Query       │
└──────────┬───────────┘
           │
           │ SMS
           ▼
┌──────────────────────────────┐
│       Android Phone          │
│                              │
│  SIM Card + SMS Service      │
│  Automate by LlamaLab        │
│                              │
│  SMS Received                │
│       │                      │
│       ▼                      │
│  HTTP Request                │
└───────┬──────────────────────┘
        │
        │ HTTP over LAN
        │
        ▼
┌──────────────────────────────┐
│       Laptop / Server        │
│                              │
│        FastAPI               │
│           │                  │
│           ▼                  │
│      LangGraph               │
│           │                  │
│           ▼                  │
│  Search + LLM Processing     │
└───────┬──────────────────────┘
        │
        │ JSON response
        │
        ▼
┌──────────────────────────────┐
│       Android Phone          │
│         Automate             │
│                              │
│      SMS Send Block          │
└──────────────┬───────────────┘
               │
               │ SMS Response
               ▼
       ┌──────────────────┐
       │ Original Sender  │
       └──────────────────┘
```

### Request flow

1. A designated sender sends an SMS query to the Android phone.
2. **Automate** detects the incoming SMS.
3. The sender's phone number and message text are extracted.
4. Automate URL-encodes the message.
5. An HTTP `GET` request is sent to the FastAPI server running on the laptop.
6. FastAPI processes the request through the AI workflow.
7. The backend returns a JSON response.
8. Automate extracts `sms_summary` from the response.
9. Automate sends the generated response back to the original sender via SMS.

---

## ⚙️ Requirements

### Android

* Android 12+
* Android phone with an active SIM card
* Working SMS service
* **Automate by LlamaLab**
* SMS permissions
* Network access to the laptop running FastAPI

### Laptop / Server

* SMS-AI-Websearch backend running locally
* FastAPI server accessible from the Android device
* Laptop and Android phone connected to the same LAN/Wi-Fi network
* A stable/static LAN IP for the laptop

### Current network setup

The current deployment uses:

```text
Android Phone
      │
      │ Same LAN
      │
      ▼
Laptop
192.168.123.123
      │
      ▼
FastAPI
```

> **Important:** `192.168.123.123` is the current server address used by this deployment. If the laptop's LAN IP changes, update the HTTP Request block in Automate.

---

# 🚀 Android Setup

## 1. Install Automate

Install **Automate by LlamaLab** on the Android device.

Create a new flow for the SMS bridge.

---

## 2. Grant Required Permissions

When the flow is started for the first time, allow the permissions requested by Automate.

The flow requires access to:

* Incoming SMS
* Sending SMS
* Network access

Automate may also request installation or activation of its required SMS/network components.

---

# 🔄 Automate Flow

The complete automation consists of three primary blocks connected in a loop:

```text
┌───────────────────┐
│   SMS Received    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   HTTP Request    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│     SMS Send      │
└─────────┬─────────┘
          │
          └──────────────► SMS Received
```

---

# 1. 📩 SMS Received Block

Configure the **SMS Received** block as follows.

### Proceed

```text
When received
```

### Message type

```text
Text
```

### Sender phone number

Configure the designated requestor:

```text
"+91XXXXXXXXXX"
```

The phone number should be entered as a quoted string and should match the intended requestor exactly.

### Output variables

Configure the block to expose:

```text
sender_phone
incoming_text
```

Where:

* `sender_phone` = phone number of the sender
* `incoming_text` = SMS message content

---

# 2. 🌐 HTTP Request Block

The HTTP Request block forwards the incoming SMS to the local FastAPI backend.

### Request URL

Enable **Expression Mode (`fx`)**.

Use:

```text
"http://192.168.123.123:8000/api/v1/search-assistant?query=" ++ urlEncode(incoming_text)
```

> Replace the host/port/path with the actual FastAPI endpoint used by your deployment.

### Request method

```text
GET
```

### Headers

Enable **Expression Mode (`fx`)** and configure:

```text
{"Connection": "keep-alive"}
```

This keeps the HTTP connection persistent while the backend processes the AI request.

### Timeout

```text
60
```

The one-minute timeout provides enough time for the backend's search and AI processing pipeline to complete.

### Save response

Enable:

```text
ON
```

Save the response as either:

```text
As text
```

or

```text
As JSON
```

### Output variable

Use:

```text
api_raw_json
```

---

# 3. 📤 SMS Send Block

The final block sends the backend response back to the original sender.

### Receiver phone number

Enable **Expression Mode (`fx`)**:

```text
sender_phone
```

This ensures that the response goes back to the phone number that initiated the request.

### Message

Enable **Expression Mode (`fx`)**:

```text
nullCoalesce(
    jsonDecode(api_raw_json)["sms_summary"],
    "Error: Response content empty"
)
```

The expression:

1. Parses the API response.
2. Extracts the `sms_summary` field.
3. Prevents an empty/null response from being sent.

### Multipart limit

```text
6
```

This allows longer responses to be split into multiple SMS messages instead of being silently truncated.

---

# 🔐 Security & Privacy

The Android bridge communicates directly with the configured FastAPI server over the local network.

```text
Android
   │
   │ HTTP
   │
   ▼
Local FastAPI Server
```

The Android SMS payload is not sent to Automate's infrastructure as part of this HTTP forwarding flow.

However, **the complete AI processing pipeline is not necessarily local**.

If the backend is configured to use a cloud LLM such as OpenAI, the relevant processed request may subsequently leave the local network.

Therefore:

* **Android → FastAPI:** Local LAN communication
* **FastAPI → SearXNG:** Depends on local SearXNG configuration
* **FastAPI → Ollama:** Local when Ollama is running locally
* **FastAPI → OpenAI:** Internet/cloud communication when OpenAI is configured as the active provider

Do not send sensitive information through the SMS bridge unless the entire backend processing path has been configured and reviewed for that use case.

---

# 🔋 Android 12+ Reliability

Android aggressively manages background applications to reduce battery consumption.

For reliable operation, configure Automate to remain active in the background.

## Disable battery optimization

On the Android device:

```text
Settings
  → Apps
  → Automate
  → Battery
  → Unrestricted
```

The exact menu names may differ depending on the Android manufacturer.

---

## Enable startup execution

Inside Automate's settings, enable:

```text
Run on system startup
```

This allows the SMS automation to restart after the phone reboots.

---

# 🌐 Network Requirements

The Android phone and laptop must be able to communicate over the LAN.

Example:

```text
Android Phone
192.168.29.x
      │
      │ Wi-Fi / LAN
      │
      ▼
Laptop
192.168.123.123
```

Before troubleshooting Automate, verify that the Android device can reach the FastAPI server.

For example, if FastAPI is running on:

```text
192.168.123.123:8000
```

the Android device must be able to establish a connection to that address.

### Important

Do not bind FastAPI only to:

```text
127.0.0.1
```

if the Android device needs to access it over the LAN.

The server should listen on the laptop's network interface, for example:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

# 🧪 Testing

Test the system from the outside in.

### 1. Test FastAPI locally

Confirm that the API is running on the laptop.

```text
Laptop
  ↓
FastAPI
  ↓
Expected JSON response
```

### 2. Test LAN connectivity

Confirm that the Android device can reach the laptop.

```text
Android
  ↓
192.168.123.123
  ↓
FastAPI
```

### 3. Test SMS reception

Send an SMS from the configured sender to the Android phone.

Expected:

```text
SMS Received
     ↓
Automate
     ↓
HTTP Request
```

### 4. Test API response

Automate should receive JSON containing:

```json
{
  "sms_summary": "..."
}
```

### 5. Test SMS delivery

Automate should extract:

```text
sms_summary
```

and send it back to:

```text
sender_phone
```

---

# 🐛 Troubleshooting

## SMS is not detected

Check:

* Automate SMS permissions
* SMS permissions in Android settings
* Sender phone number configuration
* Whether the message is actually arriving on the SIM

---

## HTTP request fails

Check:

* Android and laptop are on the same network
* Laptop IP address is correct
* FastAPI is running
* FastAPI is listening on a LAN-accessible interface
* Laptop firewall is allowing the FastAPI port
* Automate HTTP Request URL is correct

Current server address:

```text
192.168.123.123
```

---

## Request times out

The current HTTP timeout is:

```text
60 seconds
```

If the AI/search pipeline regularly takes longer than this, increase the timeout or optimize the backend workflow.

---

## SMS response is empty

Verify that the API response contains:

```json
{
  "sms_summary": "..."
}
```

Also verify that:

```text
api_raw_json
```

contains the complete HTTP response.

---

## Long responses are truncated

Increase the Automate SMS multipart limit.

Current configuration:

```text
6
```

Long SMS responses may be split into multiple messages depending on the device, carrier, encoding, and message content.

---

# 📂 Relationship to the Main Project

The Android bridge is an **optional client/integration layer** for SMS-AI-Websearch.

The core application remains:

```text
FastAPI
   ↓
LangGraph
   ↓
SearXNG
   ↓
LLM Router
   ├── OpenAI
   └── Ollama
```

The Android integration adds an SMS interface:

```text
SMS
 ↓
Android + Automate
 ↓
FastAPI
 ↓
AI Workflow
 ↓
Android + Automate
 ↓
SMS
```

The Android device therefore acts as an **SMS gateway/client**, while the laptop remains responsible for the AI processing.

---

# 📝 Current Deployment Notes

The current setup uses:

* Android phone with physical SIM
* Working SMS service
* Automate by LlamaLab
* Android 12+
* Laptop running FastAPI
* Android and laptop on the same LAN
* Static LAN IP for the laptop
* HTTP communication between Android and FastAPI
* SMS response returned through the Android SIM

The static IP currently used by the laptop is:

```text
192.168.123.123
```

If the network topology changes, update the Automate HTTP Request configuration accordingly.

---

## 🔮 Future Improvements

Potential improvements to the bridge include:

* Replace static IP with local DNS/hostname
* Add API authentication
* Replace `GET` with `POST`
* Add request IDs for tracing
* Add request/response logging
* Add retry handling in Automate
* Add backend health-check endpoint
* Add duplicate SMS protection
* Add rate limiting
* Support multiple authorized phone numbers
* Add SMS command prefixes
* Add a dedicated Android application if Automate becomes insufficient
* Add HTTPS if communication ever leaves the trusted LAN

---

## 📄 Related Documentation

See the main project README for:

* FastAPI setup
* LangGraph architecture
* SearXNG setup
* Ollama setup
* OpenAI configuration
* Environment variables
* Python development setup
* Project structure
* Contribution guidelines
