# Ollama Setup & Troubleshooting Guide

## Overview
This system uses Ollama for local LLM operations, providing AI-powered system analysis and remediation without requiring API keys.

## Quick Setup

### 1. Install Ollama
```bash
# Windows (PowerShell)
winget install Ollama.Ollama
# or download from https://ollama.com/download

# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Start Ollama Service
```bash
# Start the Ollama service
ollama serve
```

### 3. Download Required Models
```bash
# Download the default model (mistral:latest)
ollama pull mistral:latest

# Optional: Download additional models
ollama pull llama2:latest
ollama pull phi3:latest
```

### 4. Verify Installation
```bash
# Test if Ollama is running
curl http://localhost:11434/api/tags

# Should return JSON with available models
```

## Configuration

### Default Settings
- **URL**: `http://localhost:11434`
- **Model**: `mistral:latest`
- **Timeout**: 60 seconds (increased for reliability)
- **Retry Attempts**: 3
- **Retry Delay**: 2 seconds

### Custom Configuration
Edit `config.py` to modify Ollama settings:

```python
@dataclass
class OllamaConfig:
    url: str = "http://localhost:11434"
    model: str = "mistral:latest"  # Change default model
    timeout: int = 60  # Adjust timeout
    retry_attempts: int = 3
    retry_delay: int = 2
    enabled: bool = True
```

## Troubleshooting

### Common Issues & Solutions

#### 1. **Ollama Service Not Running**
**Symptoms**: Connection refused, timeout errors
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve

# On Windows, check if service is running
Get-Service -Name "Ollama"
```

#### 2. **Model Not Found**
**Symptoms**: "Default model not available" warnings
```bash
# List available models
ollama list

# Download missing model
ollama pull mistral:latest

# Check model status
ollama show mistral:latest
```

#### 3. **Request Timeouts**
**Symptoms**: "Ollama request timeout" warnings
**Solutions**:
- Increased default timeout from 30s to 60s
- Reduced `num_predict` from 1000 to 500 tokens
- Added retry logic with exponential backoff
- Optimized request parameters

#### 4. **500 Server Errors**
**Symptoms**: "Ollama request failed: 500" errors
**Solutions**:
- Restart Ollama service: `ollama serve`
- Check system resources (CPU, memory)
- Try a different model: `ollama pull llama2:latest`
- Check Ollama logs for detailed errors

#### 5. **High Memory Usage**
**Symptoms**: Slow responses, system lag
**Solutions**:
- Use smaller models: `phi3:latest` (3.8B) instead of `mixtral:8x7b` (46.7B)
- Close other applications to free memory
- Restart Ollama service periodically

#### 6. **GPU Issues (Windows)**
**Symptoms**: CUDA errors, GPU not detected
**Solutions**:
- Update GPU drivers
- Check CUDA installation
- Use CPU-only mode if needed
- Set environment variable: `OLLAMA_LLM_LIBRARY=cpu_avx2`

### Performance Optimization

#### 1. **Model Selection**
- **Fastest**: `phi3:latest` (3.8B parameters)
- **Balanced**: `mistral:latest` (7.2B parameters)
- **Most Capable**: `mixtral:8x7b` (46.7B parameters)

#### 2. **System Requirements**
- **Minimum**: 8GB RAM, 4-core CPU
- **Recommended**: 16GB RAM, 8-core CPU
- **Optimal**: 32GB RAM, dedicated GPU

#### 3. **Request Optimization**
- Reduced token limit: 500 instead of 1000
- Optimized temperature: 0.3 for consistent responses
- Added rate limiting: 5 requests per minute

### Testing Ollama Integration

Run the test suite to verify everything is working:

```bash
python test_ollama.py
```

Expected output:
```
🦙 Ollama Integration Test Suite
✅ Ollama is healthy and available
✅ Found 5 models: mistral:latest, llama2:latest, ...
✅ All tests passed! Ollama integration is working correctly.
```

### Monitoring & Logs

#### 1. **System Logs**
Check `debug_output/agent_system.log` for Ollama-related messages:
```bash
grep -i ollama debug_output/agent_system.log
```

#### 2. **Ollama Logs**
**Windows**:
```powershell
# View Ollama logs
Get-Content "$env:LOCALAPPDATA\Ollama\logs\server.log" -Tail 50
```

**Linux/macOS**:
```bash
# View Ollama logs
tail -f ~/.ollama/logs/server.log
```

#### 3. **Web Interface**
Access the LLM Status section at `http://localhost:8000` to see:
- Ollama availability
- Available models
- Current provider configuration
- Health status

### Advanced Configuration

#### 1. **Custom Model Configuration**
```python
# In config.py
self.ollama = OllamaConfig(
    url="http://localhost:11434",
    model="phi3:latest",  # Use faster model
    timeout=90,  # Increase timeout
    retry_attempts=5,  # More retries
    retry_delay=3  # Longer delays
)
```

#### 2. **Environment Variables**
```bash
# Set custom Ollama URL
export OLLAMA_HOST=0.0.0.0:11434

# Force CPU mode
export OLLAMA_LLM_LIBRARY=cpu_avx2

# Enable debug logging
export OLLAMA_DEBUG=1
```

#### 3. **Docker Setup** (Alternative)
```bash
# Run Ollama in Docker
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# Pull models
docker exec -it ollama ollama pull mistral:latest
```

### Troubleshooting Checklist

- [ ] Ollama service is running (`ollama serve`)
- [ ] Models are downloaded (`ollama list`)
- [ ] Port 11434 is accessible (`curl http://localhost:11434/api/tags`)
- [ ] System has sufficient resources (RAM, CPU)
- [ ] No firewall blocking localhost:11434
- [ ] Ollama logs show no errors
- [ ] Test suite passes (`python test_ollama.py`)

### Getting Help

1. **Check Ollama Documentation**: https://ollama.com/docs
2. **View System Logs**: `debug_output/agent_system.log`
3. **Run Test Suite**: `python test_ollama.py`
4. **Check Web Interface**: `http://localhost:8000` → LLM Status
5. **Ollama Community**: https://github.com/ollama/ollama/discussions

### Recent Fixes Applied

1. **Increased Timeout**: From 30s to 60s for better reliability
2. **Optimized Requests**: Reduced token limit and improved parameters
3. **Better Error Handling**: Enhanced retry logic and fallback responses
4. **Fixed Type Issues**: Proper aiohttp ClientTimeout usage
5. **Model Selection**: Default to `mistral:latest` with fallback logic

The system should now be much more reliable with Ollama integration! 