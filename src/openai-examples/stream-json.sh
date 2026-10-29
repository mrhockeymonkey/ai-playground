#!/usr/bin/env bash
# Usage: MISTRAL_API_KEY="..." ./stream-json.sh
set -euo pipefail

: "${MISTRAL_API_KEY:?MISTRAL_API_KEY is not set}"

PROMPT=$(cat <<'EOF'
You are a Québécois teacher/translator.

Your role is to check the below input for correctness and to suggest corrections to help the user learn French through speaking. 

## Rules: 
- If the input is good there is no need to suggest corrections or alternatives
- Grammar is not a high priority unless it is required for the meaning of a sentence. For example "Jai" should be corrected to "J'ai"
- Ignore incorrect capitalization unless it is important 
- Never use a codeblock in the response
- Never ask follow up questions

## Examples

A sentence that needs correction

Input: ils a perdu les chiens

Output:
{
  "correction": "Ils ont perdu les chiens.",
  "explanation": "**ils** → sujet pluriel\n**ont** → auxiliaire avoir au présent (3ᵉ personne du pluriel, pas « a »)\n**perdu** → participe passé de perdre",
  "suggestion": "",
  "meaning": "They lost the dogs."
}

A sentence that does not need correction

Input: On va aller à la plage

Output:
{
  "correction": "",
  "explanation": "",
  "suggestion": "En français québécois courant, on dirait souvent : « On va à la plage. » (le futur proche est déjà inclus dans « on va »).",
  "meaning": "We’re going to the beach."
}

## Input

qu'est-ce que tu veux pour dîner

EOF
)

SCHEMA=$(cat <<'EOF'
{
  "type": "object",
  "properties": {
    "correction": {"type": "string"},
    "explanation": {"type": "string"},
    "suggestion": {"type": "string"},
    "meaning": {"type": "string"}
  },
  "required": ["correction", "explanation", "suggestion", "meaning"],
  "additionalProperties": false
}
EOF
)

# Build the request with jq so the prompt is safely JSON-escaped
BODY=$(jq -n --arg prompt "$PROMPT" --argjson schema "$SCHEMA" '{
  model: "mistral-large-latest",
  stream: true,
  messages: [{role: "user", content: $prompt}],
  response_format: {
    type: "json_schema",
    json_schema: {name: "french_feedback", strict: true, schema: $schema}
  }
}')

curl -sN https://api.mistral.ai/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MISTRAL_API_KEY}" \
  -d "$BODY" |
  jq -Rj --unbuffered '
    select(startswith("data: "))
    | ltrimstr("data: ")
    | select(. != "[DONE]")
    | fromjson
    | .choices[0].delta.content // empty'

echo
