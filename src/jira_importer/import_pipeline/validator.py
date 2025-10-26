"""Description: This script contains the validator for the Jira Importer.

Author:
    Julien (@tom4897)
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence

from .models import ColumnIndices, FixOutcome, IRowRule, Problem, ValidationContext, ValidationResult


class JiraImportValidator:  # pylint: disable=too-few-public-methods
    """Runs row-level rules and (optionally) applies safe auto-fixes via a FixRegistry.

    Contract:
      validate_row(row, indices, ctx) -> ValidationResult

    Notes:
      - Rules MUST NOT mutate 'row' in-place. They return a sparse 'patch' (col_idx -> str).
      - When auto-fix is enabled and a fix registry is present, each problem is offered to the
        registry. Returned fix patches are merged (later fixes win on key conflicts).
      - This class does NOT apply patches to the original table; it only returns them.
    """

    def __init__(
        self,
        *,
        rules: Sequence[IRowRule],
        fix_registry: object | None = None,
    ) -> None:
        """Initialize the JiraImportValidator class.

        Args:
        rules: Ordered list of row rules to run.
        fix_registry: Optional object exposing
            apply(problem, row, indices, ctx) -> FixOutcome
        (A concrete registry can dispatch to IFixer instances by problem.code.)
        """
        self._rules: list[IRowRule] = list(rules)
        self._fix_registry = fix_registry

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def validate_row(
        self,
        row: Sequence[object],
        indices: ColumnIndices,
        ctx: ValidationContext,
    ) -> ValidationResult:
        """Run all rules on a single row and (optionally) apply fixes.

        Returns:
            ValidationResult(problems, patch, notes)
        """
        all_problems: list[Problem] = []
        combined_patch: dict[int, str] = {}

        # 1) Run rules in order, aggregate problems and patches
        for rule in self._rules:
            result = rule.apply(row, indices, ctx)
            if result.patch:
                _merge_patch(combined_patch, result.patch)
            if result.problems:
                all_problems.extend(result.problems)

        # 2) Auto-fix pass (optional). Do not mutate 'row' here.
        if ctx.auto_fix_enabled and self._fix_registry and all_problems:
            fix_patches: dict[int, str] = {}
            # Apply fixes in the same order problems were produced.
            for prob in all_problems:
                # Ask registry to handle this problem; registry decides if it has a fixer.
                try:
                    outcome: FixOutcome = self._fix_registry.apply(prob, row, indices, ctx)  # type: ignore[attr-defined]
                except AttributeError:
                    # Registry does not expose 'apply' → fail closed (no fixes)
                    outcome = FixOutcome(applied=False)
                except Exception:
                    # Be defensive: a buggy fixer must not break validation.
                    outcome = FixOutcome(applied=False)

                if outcome.applied and outcome.patch:
                    _merge_patch(fix_patches, outcome.patch)

            if fix_patches:
                _merge_patch(combined_patch, fix_patches)

        if not all_problems and not combined_patch:
            return ValidationResult.empty()

        return ValidationResult(
            problems=tuple(all_problems),
            patch=combined_patch,
            notes=None,
        )


# ------------------------------------------------------------------------- #
# Helpers
# ------------------------------------------------------------------------- #


def _merge_patch(dest: MutableMapping[int, str], src: Mapping[int, str]) -> None:
    """Merge sparse patches. Later writes win on the same column index.

    Values are expected to be strings (post-normalization contract).
    """
    for k, v in src.items():
        # Skip clearly invalid indices; leave bounds checking to the applier.
        if not isinstance(k, int):
            continue
        dest[k] = v
