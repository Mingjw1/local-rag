#!/bin/bash
# 快速功能测试
set -e

BASE_URL="${API_URL:-http://localhost:8005}"
PASS=0
FAIL=0

green() { echo -e "\033[32m$1\033[0m"; }
red() { echo -e "\033[31m$1\033[0m"; }

# 1. 健康检查
echo ">>> 1. 健康检查"
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q '"status":"ok"'; then
  green "  ✓ 服务正常"
  PASS=$((PASS + 1))
else
  red "  ❌ 服务异常: $HEALTH"
  FAIL=$((FAIL + 1))
fi

# 2. 创建知识库
echo ">>> 2. 创建知识库"
KB=$(curl -s -X POST "$BASE_URL/api/v1/knowledge-bases" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试知识库","description":"功能测试"}')
KB_ID=$(echo "$KB" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
if [ -n "$KB_ID" ]; then
  green "  ✓ 知识库已创建: $KB_ID"
  PASS=$((PASS + 1))
else
  red "  ❌ 创建失败: $KB"
  FAIL=$((FAIL + 1))
fi

# 3. 上传文档
echo ">>> 3. 上传文档"
DOC=$(curl -s -X POST "$BASE_URL/api/v1/knowledge-bases/$KB_ID/documents" \
  -F "file=@-;filename=test.md" \
  -F "title=测试文档" <<< "# Test\n## Hello\nThis is a test document for the RAG system.")
DOC_STATUS=$(echo "$DOC" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "")
if [ "$DOC_STATUS" = "ready" ]; then
  green "  ✓ 文档导入成功"
  PASS=$((PASS + 1))
else
  red "  ❌ 导入失败: $DOC"
  FAIL=$((FAIL + 1))
fi

# 4. 搜索
echo ">>> 4. 搜索测试"
SEARCH=$(curl -s -X POST "$BASE_URL/api/v1/knowledge-bases/$KB_ID/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","top_k":3}')
SEARCH_COUNT=$(echo "$SEARCH" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
if [ "$SEARCH_COUNT" -gt 0 ]; then
  green "  ✓ 搜索返回 $SEARCH_COUNT 条结果"
  PASS=$((PASS + 1))
else
  red "  ❌ 搜索失败: $SEARCH"
  FAIL=$((FAIL + 1))
fi

# 5. 问答
echo ">>> 5. 问答测试"
QA=$(curl -s -X POST "$BASE_URL/api/v1/knowledge-bases/$KB_ID/query" \
  -H "Content-Type: application/json" \
  -d '{"query":"这个文档说了什么？","top_k":3}')
QA_LEN=$(echo "$QA" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['answer']))" 2>/dev/null || echo "0")
if [ "$QA_LEN" -gt 10 ]; then
  green "  ✓ 问答生成长度: ${QA_LEN} 字符"
  PASS=$((PASS + 1))
else
  red "  ❌ 问答失败: $QA"
  FAIL=$((FAIL + 1))
fi

# 6. Wiki 页面
echo ">>> 6. Wiki 页面检查"
WIKI=$(curl -s "$BASE_URL/api/v1/knowledge-bases/$KB_ID/wiki/pages")
WIKI_COUNT=$(echo "$WIKI" | python3 -c "import sys,json; print(json.load(sys.stdin)['total'])" 2>/dev/null || echo "0")
if [ "$WIKI_COUNT" -gt 0 ]; then
  green "  ✓ Wiki 有 $WIKI_COUNT 个页面"
  PASS=$((PASS + 1))
else
  red "  ❌ Wiki 页面为空"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "=== 测试结果 ==="
if [ "$FAIL" -eq 0 ]; then
  green "全部通过: $PASS/$((PASS + FAIL))"
  exit 0
else
  red "通过: $PASS, 失败: $FAIL"
  exit 1
fi
