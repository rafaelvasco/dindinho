"""CSV parser for credit card statements and account extracts."""

import pandas as pd
import json
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging

from backend.utils.date_parser import parse_brazilian_date
from backend.utils.currency_parser import parse_brl_currency

logger = logging.getLogger(__name__)


class CSVParser:
    """
    Parser for Brazilian CSV files (credit card statements and account extracts).

    Supports two formats:
    1. Credit Card Statement (comma-delimited)
    2. Account Extract (semicolon-delimited, skip first 5 lines)
    """

    @staticmethod
    def detect_format(file_path: str) -> str:
        """
        Auto-detect CSV format by analyzing the file structure.

        Args:
            file_path: Path to the CSV file

        Returns:
            "credit_card" or "account_extract"

        Raises:
            ValueError: If format cannot be detected
        """
        try:
            # Read first few lines to detect format
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                first_lines = [f.readline() for _ in range(6)]

            # Check for semicolon delimiter (account extract)
            if any(';' in line for line in first_lines):
                # Account extract has "Data Lançamento;Descrição;Valor;Saldo" header
                if any('Data Lançamento' in line or 'Descrição' in line for line in first_lines):
                    logger.info("Detected format: account_extract (semicolon delimiter)")
                    return "account_extract"

            # Check for comma delimiter with "Data" column (credit card)
            if any(',' in line for line in first_lines):
                if any('Data' in line and 'Lançamento' in line for line in first_lines):
                    logger.info("Detected format: credit_card (comma delimiter)")
                    return "credit_card"

            raise ValueError("Could not detect CSV format")

        except Exception as e:
            logger.error(f"Error detecting format: {e}")
            raise ValueError(f"Error detecting CSV format: {e}")

    @staticmethod
    def is_credit_card_payment(description: str) -> bool:
        """
        Detect if a bank transaction is a credit card payment.

        Common Brazilian bank patterns for credit card payments:
        - PAGAMENTO CARTAO / PAG CARTAO / PGTO CARTAO
        - FATURA CARTAO / FATURA CREDITO
        - PAG FATURA / PGTO FATURA
        - CARTAO DE CREDITO / CARTAO CREDITO

        Args:
            description: Transaction description from bank extract

        Returns:
            True if the description matches credit card payment patterns
        """
        # Normalize: uppercase, remove extra spaces
        normalized = description.upper().strip()

        # Define payment patterns
        # Use tuples of required terms - ALL must be present
        required_patterns = [
            ['PAGAMENTO', 'CARTAO'],
            ['PAGAMENTO', 'FATURA'],
            ['PAG', 'CARTAO'],
            ['PAG', 'FATURA'],
            ['PGTO', 'CARTAO'],
            ['PGTO', 'FATURA'],
            ['FATURA', 'CARTAO'],
            ['FATURA', 'CREDITO'],
            ['CARTAO', 'CREDITO'],
        ]

        # Check if any pattern matches
        for pattern_terms in required_patterns:
            if all(term in normalized for term in pattern_terms):
                logger.debug(f"Credit card payment detected: {description}")
                return True

        return False

    @staticmethod
    def parse_credit_card(file_path: str) -> List[Dict]:
        """
        Parse credit card statement CSV file.

        Format:
            "Data","Lançamento","Categoria","Tipo","Valor"
            "03/01/2026","APPLE.COM/BILL","COMPRAS","Compra à vista","R$ 119,90"

        Args:
            file_path: Path to the CSV file

        Returns:
            List of dictionaries with parsed expense data
        """
        expenses = []

        try:
            # Try encodings common for Brazilian files
            encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1', 'latin-1']
            df = None

            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, delimiter=',')
                    logger.info(f"Successfully read file with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue

            if df is None:
                raise ValueError("Could not read file with any supported encoding")

            # Process each row
            for idx, row in df.iterrows():
                try:
                    # Parse date
                    date_str = str(row.get('Data', '')).strip()
                    date = parse_brazilian_date(date_str)

                    if not date:
                        logger.warning(f"Row {idx}: Could not parse date '{date_str}', skipping")
                        continue

                    # Parse amount
                    amount_str = str(row.get('Valor', '')).strip()
                    raw_amount = parse_brl_currency(amount_str)

                    if raw_amount is None:
                        logger.warning(f"Row {idx}: Could not parse amount '{amount_str}', skipping")
                        continue

                    # Transform amount to absolute value and determine transaction type
                    # Credit card: positive = EXPENSE (adding to debt), negative = REFUND
                    amount = abs(raw_amount)
                    transaction_type = 'EXPENSE' if raw_amount > 0 else 'REFUND'

                    # Get description
                    description = str(row.get('Lançamento', '')).strip()

                    if not description:
                        logger.warning(f"Row {idx}: Empty description, skipping")
                        continue

                    # Build transaction dict
                    transaction = {
                        'date': date,
                        'description': description,
                        'amount': amount,
                        'transaction_type': transaction_type,
                        'original_category': str(row.get('Categoria', '')).strip() or None,
                        'source_type': 'credit_card',
                        'raw_data': json.dumps(row.to_dict(), default=str, ensure_ascii=False)
                    }

                    expenses.append(transaction)

                except Exception as e:
                    logger.error(f"Row {idx}: Error parsing - {e}")
                    continue

            logger.info(f"Parsed {len(expenses)} expenses from credit card statement")
            return expenses

        except Exception as e:
            logger.error(f"Error parsing credit card CSV: {e}")
            raise ValueError(f"Error parsing credit card CSV: {e}")

    @staticmethod
    def parse_account_extract(file_path: str) -> List[Dict]:
        """
        Parse account extract CSV file.

        Format (skip first 5 lines):
            Extrato Conta Corrente
            Conta ;31304761
            Período ;01/12/2025 a 31/12/2025
            Saldo: ;6.866,58

            Data Lançamento;Descrição;Valor;Saldo
            01/12/2025;Pix enviado: "Cp :90400888-ORGANIZACAO VERDEMAR LTDA";-703,69;1.008,71

        Args:
            file_path: Path to the CSV file

        Returns:
            List of dictionaries with parsed expense data
        """
        expenses = []

        try:
            # Try encodings common for Brazilian files
            encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1', 'latin-1']
            df = None

            for encoding in encodings:
                try:
                    # Skip first 5 lines, use semicolon delimiter
                    df = pd.read_csv(file_path, encoding=encoding, delimiter=';', skiprows=5)
                    logger.info(f"Successfully read file with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    continue

            if df is None:
                raise ValueError("Could not read file with any supported encoding")

            # Clean column names (remove extra spaces)
            df.columns = df.columns.str.strip()

            # Process each row
            for idx, row in df.iterrows():
                try:
                    # Parse date
                    date_str = str(row.get('Data Lançamento', '')).strip()
                    date = parse_brazilian_date(date_str)

                    if not date:
                        logger.warning(f"Row {idx}: Could not parse date '{date_str}', skipping")
                        continue

                    # Parse amount
                    amount_str = str(row.get('Valor', '')).strip()
                    raw_amount = parse_brl_currency(amount_str)

                    if raw_amount is None:
                        logger.warning(f"Row {idx}: Could not parse amount '{amount_str}', skipping")
                        continue

                    # Get description (moved earlier to enable payment detection)
                    description = str(row.get('Descrição', '')).strip()

                    if not description:
                        logger.warning(f"Row {idx}: Empty description, skipping")
                        continue

                    # Transform amount to absolute value and determine transaction type
                    amount = abs(raw_amount)

                    # Determine transaction type based on amount sign and description
                    if raw_amount < 0:
                        # Money leaving account - check if it's a credit card payment
                        if CSVParser.is_credit_card_payment(description):
                            transaction_type = 'PAYMENT'
                            logger.info(f"Row {idx}: Detected credit card payment: {description}")
                        else:
                            transaction_type = 'EXPENSE'
                    else:
                        # Money entering account
                        transaction_type = 'INCOME'

                    # Build transaction dict
                    transaction = {
                        'date': date,
                        'description': description,
                        'amount': amount,
                        'transaction_type': transaction_type,
                        'original_category': None,
                        'source_type': 'account_extract',
                        'raw_data': json.dumps(row.to_dict(), default=str, ensure_ascii=False)
                    }

                    expenses.append(transaction)

                except Exception as e:
                    logger.error(f"Row {idx}: Error parsing - {e}")
                    continue

            logger.info(f"Parsed {len(expenses)} expenses from account extract")
            return expenses

        except Exception as e:
            logger.error(f"Error parsing account extract CSV: {e}")
            raise ValueError(f"Error parsing account extract CSV: {e}")

    def parse(self, file_path: str) -> Tuple[str, List[Dict]]:
        """
        Auto-detect format and parse CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            Tuple of (format_type, list of expenses)

        Raises:
            ValueError: If file cannot be parsed
        """
        # Detect format
        format_type = self.detect_format(file_path)

        # Parse based on format
        if format_type == "credit_card":
            expenses = self.parse_credit_card(file_path)
        elif format_type == "account_extract":
            expenses = self.parse_account_extract(file_path)
        else:
            raise ValueError(f"Unknown format type: {format_type}")

        return format_type, expenses
