# Agent Instructions (All Projects)

## CRITICAL: Protected Ports - DO NOT KILL

The following ports are reserved for system services. NEVER kill processes on these ports:

- **Port 3008** - Devchain application (CRITICAL - killing this crashes the entire system)
- **Ports 3000-3010** - Reserved system range

## When starting a dev server:

1. Use ports **4000 or higher** (4000, 5000, 5173, 8080, etc.)
2. Set PORT environment variable: `PORT=4000 npm run dev`
3. If a port is busy, increment to the next available

## FORBIDDEN commands:

```bash
# NEVER run these on ports 3000-3010:
fuser -k 3000/tcp    # FORBIDDEN
fuser -k 3008/tcp    # FORBIDDEN  
kill $(lsof -t -i:3000)  # FORBIDDEN
pkill -f "port 3000"     # FORBIDDEN
```

## Safe alternatives:

```bash
# Find what's using a port (read-only, safe)
lsof -i :3000

# Start dev server on a different port
PORT=4000 npm start
npm run dev -- --port 5173
```
