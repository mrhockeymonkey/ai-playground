#! /bin/bash

curl https://openrouter.ai/api/alpha/decisions \-H "Content-Type: application/json" \-H "Authorization: Bearer $OPENROUTER_API_KEY" \-d @risk-example.json