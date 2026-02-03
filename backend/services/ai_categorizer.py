"""AI categorizer service using Claude for transaction categorization."""

import json
import logging
from typing import List, Dict, Optional
from anthropic import Anthropic
from backend.config import settings
from backend.models.category import TransactionCategory

logger = logging.getLogger(__name__)


class AICategorizer:
    """
    Service for categorizing transactions using Claude AI.

    Uses Claude to analyze transaction descriptions and assign appropriate
    Brazilian transaction categories.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the AI categorizer.

        Args:
            api_key: Anthropic API key (defaults to settings.ANTHROPIC_API_KEY)
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.client = Anthropic(api_key=self.api_key)
        self.cache: Dict[str, str] = {}  # Simple in-memory cache

    def categorize_single(self, description: str) -> str:
        """
        Categorize a single transaction description.

        Args:
            description: Transaction description

        Returns:
            Category name (Portuguese)
        """
        # Check cache first
        if description in self.cache:
            logger.debug(f"Cache hit for: {description}")
            return self.cache[description]

        # Categorize using batch method
        categories = self.categorize_batch([description])
        return categories[0] if categories else TransactionCategory.OTHER.value

    def categorize_batch(self, descriptions: List[str]) -> List[str]:
        """
        Categorize multiple transaction descriptions efficiently.

        Args:
            descriptions: List of transaction descriptions

        Returns:
            List of category names (same order as input)
        """
        if not descriptions:
            return []

        # Check cache and identify uncached items
        results = []
        uncached_indices = []
        uncached_descriptions = []

        for i, desc in enumerate(descriptions):
            if desc in self.cache:
                results.append(self.cache[desc])
                logger.debug(f"Cache hit for: {desc}")
            else:
                results.append(None)  # Placeholder
                uncached_indices.append(i)
                uncached_descriptions.append(desc)

        # If all cached, return immediately
        if not uncached_descriptions:
            return results

        logger.info(f"Categorizing {len(uncached_descriptions)} transactions with Claude AI")

        try:
            # Build prompt for Claude
            prompt = self._build_prompt(uncached_descriptions)

            # Call Claude API (using Haiku 4.5 - fast and cost-effective)
            message = self.client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            response_text = message.content[0].text
            categories = self._parse_response(response_text, uncached_descriptions)

            # Update results and cache
            for idx, category in zip(uncached_indices, categories):
                results[idx] = category
                self.cache[descriptions[idx]] = category

            return results

        except Exception as e:
            logger.error(f"Error categorizing transactions: {e}")
            # Fallback to "Outros" for uncategorized items
            for idx in uncached_indices:
                results[idx] = TransactionCategory.OTHER.value
            return results

    def _build_prompt(self, descriptions: List[str]) -> str:
        """
        Build prompt for Claude with transaction descriptions and categories.

        Args:
            descriptions: List of transaction descriptions

        Returns:
            Formatted prompt string
        """
        # Get all categories but exclude "Assinaturas" (reserved for manual subscription marking)
        all_categories = TransactionCategory.get_all_categories()
        categories = [cat for cat in all_categories if cat != TransactionCategory.SUBSCRIPTIONS.value]

        prompt = f"""Você é um assistente especializado em categorizar despesas financeiras no Brasil.

Categorias disponíveis:
{json.dumps(categories, ensure_ascii=False, indent=2)}

Analise as seguintes descrições de despesas e atribua a categoria mais apropriada para cada uma.
Retorne sua resposta como um array JSON com as categorias na mesma ordem das despesas.

Descrições:
{json.dumps(descriptions, ensure_ascii=False, indent=2)}

IMPORTANTE:
- Retorne APENAS um array JSON com as categorias
- Use exatamente os nomes das categorias fornecidos acima
- A ordem das categorias deve corresponder à ordem das descrições
- Considere o contexto brasileiro (nomes de empresas, serviços, etc.)
- NUNCA use "Assinaturas" - essa categoria é reservada apenas para itens marcados manualmente como assinaturas
- Para serviços recorrentes (Netflix, Spotify, etc.), use a categoria mais apropriada como "Entretenimento"

Exemplos:
- "NETFLIX.COM" -> "Entretenimento"
- "SPOTIFY PREMIUM" -> "Entretenimento"
- "UBER TRIP" -> "Transporte"
- "SUPERMERCADO EXTRA" -> "Supermercado"
- "FARMACIA POPULAR" -> "Saúde"
- "RESTAURANTE GOURMET" -> "Restaurantes"

Resposta (apenas o array JSON):"""

        return prompt

    def _parse_response(self, response_text: str, descriptions: List[str]) -> List[str]:
        """
        Parse Claude's response and extract categories.

        Args:
            response_text: Claude's response text
            descriptions: Original descriptions (for length validation)

        Returns:
            List of categories
        """
        try:
            # Try to parse as JSON array
            # Remove any markdown code blocks if present
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```"):
                # Remove markdown code block markers
                cleaned_response = cleaned_response.split("\n", 1)[1]
                cleaned_response = cleaned_response.rsplit("```", 1)[0]
                cleaned_response = cleaned_response.strip()

            categories = json.loads(cleaned_response)

            # Validate that we got the right number of categories
            if len(categories) != len(descriptions):
                logger.warning(
                    f"Category count mismatch: expected {len(descriptions)}, "
                    f"got {len(categories)}"
                )
                # Pad or truncate to match
                while len(categories) < len(descriptions):
                    categories.append(TransactionCategory.OTHER.value)
                categories = categories[:len(descriptions)]

            # Validate each category
            valid_categories = TransactionCategory.get_all_categories()
            for i, category in enumerate(categories):
                if category not in valid_categories:
                    logger.warning(f"Invalid category '{category}', using 'Outros'")
                    categories[i] = TransactionCategory.OTHER.value

            return categories

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            # Fallback to "Outros" for all
            return [TransactionCategory.OTHER.value] * len(descriptions)
        except Exception as e:
            logger.error(f"Error parsing Claude response: {e}")
            return [TransactionCategory.OTHER.value] * len(descriptions)

    def clear_cache(self):
        """Clear the categorization cache."""
        self.cache.clear()
        logger.info("Categorization cache cleared")
