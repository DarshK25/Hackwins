#!/bin/bash

# MoneyOps API Gateway - Phase 3 Quick Start
# Complete setup for Rate Limiting with Redis

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=================================================="
echo "MoneyOps API Gateway - Phase 3 Setup"
echo "Rate Limiting with Redis"
echo "=================================================="
echo ""

# Step 1: Check Prerequisites
echo -e "${BLUE}Step 1: Checking Prerequisites${NC}"
echo ""

if command -v java &> /dev/null; then
    echo -e "${GREEN}✓${NC} Java installed"
else
    echo -e "${RED}✗${NC} Java not found. Please install Java 17+"
    exit 1
fi

if command -v mvn &> /dev/null; then
    echo -e "${GREEN}✓${NC} Maven installed"
else
    echo -e "${RED}✗${NC} Maven not found. Please install Maven 3.8+"
    exit 1
fi

if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker installed"
else
    echo -e "${RED}✗${NC} Docker not found. Please install Docker"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker Compose installed"
else
    echo -e "${RED}✗${NC} Docker Compose not found. Please install Docker Compose"
    exit 1
fi

echo ""

# Step 2: Start Redis
echo -e "${BLUE}Step 2: Starting Redis${NC}"
echo ""

echo "Starting Redis container..."
docker-compose up -d redis

echo "Waiting for Redis to be ready..."
sleep 3

# Verify Redis is running
if docker exec moneyops-redis redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✓${NC} Redis is running and healthy"
else
    echo -e "${RED}✗${NC} Redis failed to start"
    echo "Check logs: docker logs moneyops-redis"
    exit 1
fi

echo ""

# Step 3: Build the Project
echo -e "${BLUE}Step 3: Building the Gateway${NC}"
echo ""

mvn clean package -DskipTests

echo -e "${GREEN}✓${NC} Build complete"
echo ""

# Step 4: Configure Environment
echo -e "${BLUE}Step 4: Configuring Environment${NC}"
echo ""

export JWT_SECRET="your-256-bit-secret-your-256-bit-secret-your-256-bit-secret-your-256-bit-secret"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export BACKEND_CORE_URL="http://localhost:8081"
export AI_GATEWAY_URL="http://localhost:8082"
export VOICE_SERVICE_URL="http://localhost:8083"

echo -e "${GREEN}✓${NC} Environment variables set"
echo ""

# Step 5: Start the Gateway
echo -e "${BLUE}Step 5: Starting the Gateway${NC}"
echo ""

echo "Starting gateway in background..."
nohup mvn spring-boot:run -Dspring-boot.run.profiles=dev > gateway.log 2>&1 &
GATEWAY_PID=$!

echo "Waiting for gateway to start..."
sleep 15

# Verify gateway is running
if curl -s http://localhost:8080/actuator/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Gateway is running (PID: $GATEWAY_PID)"
else
    echo -e "${RED}✗${NC} Gateway failed to start"
    echo "Check logs: tail -f gateway.log"
    exit 1
fi

echo ""

# Step 6: Verify Redis Health
echo -e "${BLUE}Step 6: Verifying Redis Integration${NC}"
echo ""

REDIS_HEALTH=$(curl -s http://localhost:8080/actuator/health | grep -o '"redis":{"status":"[^"]*"')

if echo "$REDIS_HEALTH" | grep -q "UP"; then
    echo -e "${GREEN}✓${NC} Redis health check: UP"
else
    echo -e "${YELLOW}⚠${NC} Redis health check: DOWN or not configured"
fi

echo ""

# Step 7: Test Rate Limiting
echo -e "${BLUE}Step 7: Testing Rate Limiting${NC}"
echo ""

echo "Making test request to check rate limit headers..."
RESPONSE=$(curl -s -v http://localhost:8080/actuator/health 2>&1)

LIMIT=$(echo "$RESPONSE" | grep -i "X-RateLimit-Limit" | awk '{print $3}' | tr -d '\r')
REMAINING=$(echo "$RESPONSE" | grep -i "X-RateLimit-Remaining" | awk '{print $3}' | tr -d '\r')

if [ -n "$LIMIT" ]; then
    echo -e "${GREEN}✓${NC} Rate limiting is working!"
    echo "  Limit: $LIMIT"
    echo "  Remaining: $REMAINING"
else
    echo -e "${YELLOW}⚠${NC} Rate limit headers not found"
fi

echo ""

# Success Summary
echo "=================================================="
echo -e "${GREEN}✓ Phase 3 Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "📊 Services Running:"
echo "  - Redis: http://localhost:6379"
echo "  - Gateway: http://localhost:8080"
echo "  - Redis Commander: http://localhost:8081 (optional)"
echo ""
echo "🧪 Test Commands:"
echo ""
echo "1. Check Health:"
echo "   curl http://localhost:8080/actuator/health | jq"
echo ""
echo "2. Run Rate Limit Tests:"
echo "   ./test-rate-limit.sh"
echo ""
echo "3. Check Redis Keys:"
echo "   docker exec -it moneyops-redis redis-cli"
echo "   > KEYS rate_limit:*"
echo ""
echo "4. View Gateway Logs:"
echo "   tail -f gateway.log"
echo ""
echo "=================================================="
echo "📋 Rate Limit Configuration:"
echo "=================================================="
echo "  Login:        5 req/sec  (IP-based)"
echo "  Register:     2 req/sec  (IP-based)"
echo "  User APIs:   50 req/sec  (User-based)"
echo "  Tenant APIs: 30 req/sec  (Org-based)"
echo "  AI Chat:      5 req/sec  (Org-based)"
echo "  AI Voice:     3 req/sec  (Org-based)"
echo "=================================================="
echo ""
echo "🛑 To Stop:"
echo "  - Gateway: kill $GATEWAY_PID"
echo "  - Redis: docker-compose down"
echo ""
echo "📚 Documentation:"
echo "  - Full Guide: cat PHASE3_README.md"
echo "  - Tracker: cat IMPLEMENTATION_TRACKER.md"
echo "=================================================="