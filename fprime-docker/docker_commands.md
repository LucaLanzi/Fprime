# F´ and Yocto Docker Setup with Docker Compose

This guide covers running NASA F´ (fprime) and NXP Yocto BSP development environments using Docker Compose on macOS.

## Overview

- **fprime-dev**: NASA F´ ARM cross-compilation container for building F´ projects
- **yocto-builder**: NXP Yocto BSP builder for embedded Linux development

Both services run in parallel on a shared Docker network, with shared access to workspace, BSP, and build artifact directories.

**Reference Documentation**: 
- [NASA F´ macOS Cross-Compilation](https://nasa.github.io/fprime/Tutorials/CrossCompilationSetup/macOS.html)
- [SCALES IMX Yocto BSP](https://scales-docs.readthedocs.io/en/latest/imx_yocto_bsp/)

## Prerequisites

1. **Install Docker Desktop**
   ```bash
   brew install --cask docker
   ```
   Ensure Docker daemon is running before proceeding.

2. **Docker Compose** (included with Docker Desktop)

3. **Update `docker-compose.yml` paths** to match your local directories:
   - `/Users/luquito/Documents/GitHub/fprime-scales-ref` → your workspace
   - `/Users/luquito/BSP-Yocto-NXP-i.MX8X-PD24.1.y` → your BSP directory
   - `/Users/luquito/build-artifacts` → your build output directory

## What `docker-compose.yml` Does

The compose file defines two services that share a network and mounted volumes:

| Service | Purpose | Image |
|---------|---------|-------|
| `fprime-dev` | NASA F´ ARM cross-compilation | `nasafprime/fprime-arm:latest` |
| `yocto-builder` | NXP Yocto BSP / Bitbake builds | `docker.io/phybuilder/yocto-ubuntu-22.04` |

### Shared Volume Mounts

```
Host Path                                    → Container Path
/workspace/fprime-scales-ref                 → /workspace
/BSP-Yocto-NXP-i.MX8X-PD24.1.y              → /bsp
/build-artifacts                             → /artifacts
```

Both containers can read/write to these directories, allowing seamless collaboration.

## Getting Started

### Step 1: Configure Paths

Edit `docker-compose.yml` and update the volume paths to match your system:

```yaml
volumes:
  - /YOUR/LOCAL/WORKSPACE:/workspace
  - /YOUR/LOCAL/BSP:/bsp
  - /YOUR/LOCAL/ARTIFACTS:/artifacts
```

### Step 2: Pull and Start Services

```bash
# Pull the latest images
docker-compose pull

# Start both containers in background
docker-compose up -d
```

### Step 3: Access a Service

Enter the F´ container:
```bash
docker attach fprime-dev
```

Or access the Yocto builder:
```bash
docker attach yocto-builder
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `docker-compose up -d` | Start all services in background |
| `docker-compose down` | Stop and remove all services |
| `docker-compose ps` | List running services |
| `docker attach fprime-dev` | Enter F´ container |
| `docker attach yocto-builder` | Enter Yocto container |
| `docker-compose logs fprime-dev` | View F´ container logs |
| `docker-compose restart yocto-builder` | Restart Yocto service |

## Working Inside Containers

### F´ Development - Initial Setup

Once inside the container, set up the Python environment:

```bash
docker attach fprime-dev

# Install python3-venv
sudo apt-get update
sudo apt-get install python3-venv

# Clean up any partial venv and run setup
rm -rf fprime-venv
make setup
```

This creates the virtual environment and installs all F´ dependencies.

### F´ Development - Building Projects

```bash
cd /workspace
fprime-util build
fprime-gds
```

### Yocto Build System

```bash
docker attach yocto-builder
cd /bsp/yocto
phyLinux init -p imx8x -r BSP-Yocto-NXP-i.MX8X-PD24.1.y
```

## Troubleshooting

### Images won't pull
```bash
# Ensure you're authenticated and can access public registries
docker login

# Manually pull images first
docker pull nasafprime/fprime-arm:latest
docker pull docker.io/phybuilder/yocto-ubuntu-22.04
```

### Container exits immediately
```bash
# Check service logs
docker-compose logs fprime-dev
docker-compose logs yocto-builder

# Restart services
docker-compose restart
```

### Permission issues in mounted volumes
Ensure your local paths have proper permissions:
```bash
chmod 755 /YOUR/LOCAL/WORKSPACE
chmod 755 /YOUR/LOCAL/BSP
chmod 755 /YOUR/LOCAL/ARTIFACTS
```

## References

- [NASA F´ Official Docs](https://nasa.github.io/fprime/)
- [F´ macOS Cross-Compilation](https://nasa.github.io/fprime/Tutorials/CrossCompilationSetup/macOS.html)
- [SCALES IMX Yocto BSP](https://scales-docs.readthedocs.io/en/latest/imx_yocto_bsp/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
