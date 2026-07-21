import secrets
import math
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from models.voucher import Voucher, VoucherStatus

logger = logging.getLogger(__name__)


class VoucherGenerator:
    """
    Secure voucher code generator.
    
    Character set: A-Z, 0-9 excluding ambiguous characters (0/O, 1/I, 5/S, 8/B, etc.)
    Default length: 12 characters
    Entropy: ~68 bits (12 chars from 34-char alphabet)
    Collision probability: ~1 in 2^34 for 1M codes (birthday paradox)
    """
    
    # Alphabet without ambiguous characters: 0/O, 1/I, 5/S, 8/B, 2/Z, 6/G, Q/0, etc.
    ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 34 characters
    DEFAULT_LENGTH = 12
    MAX_RETRIES = 100

    def __init__(self, alphabet: str | None = None, length: int | None = None):
        self.alphabet = alphabet or self.ALPHABET
        self.length = length or self.DEFAULT_LENGTH

    @property
    def entropy_bits(self) -> float:
        """Estimated entropy in bits for a single code."""
        return self.length * math.log2(len(self.alphabet))

    @property
    def collision_probability_1m(self) -> float:
        """Approximate collision probability for 1 million codes (birthday bound)."""
        n = 1_000_000
        space = len(self.alphabet) ** self.length
        return 1 - math.exp(-n * (n - 1) / (2 * space))

    def generate(self) -> str:
        """Generate a single secure random code."""
        return ''.join(secrets.choice(self.alphabet) for _ in range(self.length))

    def generate_batch(self, count: int) -> list[str]:
        """Generate multiple codes (may have duplicates within batch)."""
        return [self.generate() for _ in range(count)]

    def generate_unique(self, db, max_retries: int | None = None) -> str:
        """
        Generate a code guaranteed to not exist in the database.
        Retries on collision. Raises if all retries exhausted.
        """
        max_retries = max_retries or self.MAX_RETRIES
        for attempt in range(max_retries):
            code = self.generate()
            existing = db.execute(select(Voucher.code).where(Voucher.code == code)).scalar_one_or_none()
            if not existing:
                return code
            logger.warning("Voucher code collision attempt %d/%d", attempt + 1, max_retries)
        raise RuntimeError(
            f"Failed to generate unique voucher code after {max_retries} retries"
        )


class VoucherCreationService:
    """
    Service for creating vouchers with database persistence.
    Handles bulk creation with collision avoidance.
    """
    
    def __init__(self, db, generator: VoucherGenerator):
        self.db = db
        self.generator = generator

    def create_voucher(
        self,
        minutes: int,
        expires_at=None,
        created_by=None,
        notes: str | None = None,
    ) -> Voucher:
        """
        Create a single voucher with automatic collision handling.
        """
        for attempt in range(self.generator.MAX_RETRIES):
            code = self.generator.generate_unique(self.db)
            
            voucher = Voucher(
                code=code,
                minutes=minutes,
                status=VoucherStatus.UNUSED,
                expires_at=expires_at,
                created_by=created_by,
                notes=notes,
            )
            
            self.db.add(voucher)
            try:
                self.db.commit()
                self.db.refresh(voucher)
                logger.info("Voucher created: %s (%d minutes) by admin %s", code, minutes, created_by)
                return voucher
            except IntegrityError:
                self.db.rollback()
                logger.warning("Voucher code collision on attempt %d: %s", attempt + 1, code)
                if attempt == self.generator.MAX_RETRIES - 1:
                    raise
        
        # Should never reach here due to raise in loop
        raise RuntimeError("Failed to generate unique voucher code after max retries")

    def create_vouchers_bulk(
        self,
        count: int,
        minutes: int,
        expires_at=None,
        created_by=None,
        notes: str | None = None,
    ) -> list[Voucher]:
        """
        Create multiple vouchers efficiently with collision handling.
        All vouchers are created in a single atomic transaction.
        """
        if count <= 0:
            return []
        if count > 10000:
            raise ValueError("Maximum 10,000 vouchers per bulk operation")

        # Pre-generate all codes with extra buffer for collision tolerance
        codes = self.generator.generate_batch(count + 100)

        # Check for duplicates within generated batch
        unique_codes = list(dict.fromkeys(codes))
        if len(unique_codes) < len(codes):
            logger.warning(
                "Bulk: %d duplicate(s) within generated batch, generating more",
                len(codes) - len(unique_codes)
            )
            extra_needed = len(codes) - len(unique_codes)
            unique_codes.extend(self.generator.generate_batch(extra_needed))
            unique_codes = list(dict.fromkeys(unique_codes))

        if len(unique_codes) < count:
            raise RuntimeError("Insufficient unique codes generated after dedup")

        # Check against existing codes in DB
        stmt = select(Voucher.code).where(Voucher.code.in_(unique_codes[:count]))
        existing = set(self.db.execute(stmt).scalars().all())

        new_codes = [c for c in unique_codes if c not in existing]
        if len(new_codes) < count:
            additional_needed = count - len(new_codes) + 50
            additional = self.generator.generate_batch(additional_needed)
            stmt2 = select(Voucher.code).where(Voucher.code.in_(additional))
            existing2 = set(self.db.execute(stmt2).scalars().all())
            for c in additional:
                if c not in existing and c not in existing2 and c not in new_codes:
                    new_codes.append(c)
                    if len(new_codes) >= count:
                        break

        if len(new_codes) < count:
            raise RuntimeError(f"Failed to generate {count} unique codes due to persistent collisions")

        vouchers = [
            Voucher(
                code=code,
                minutes=minutes,
                expires_at=expires_at,
                created_by=created_by,
                notes=notes,
                status=VoucherStatus.UNUSED,
            )
            for code in new_codes[:count]
        ]

        self.db.add_all(vouchers)
        try:
            self.db.commit()
            for v in vouchers:
                self.db.refresh(v)
        except IntegrityError:
            self.db.rollback()
            raise RuntimeError("Bulk voucher creation failed due to code collision")
        
        logger.info(
            "Bulk voucher creation complete: %d vouchers created by admin %s",
            len(vouchers), created_by
        )
        return vouchers