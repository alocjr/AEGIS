"""Motor de regras de Governança (R1-R4): tabelas de decisão puras, sem I/O nem DB."""

from __future__ import annotations

import copy
import unittest

from app.governance.rules.r1_maturidade import (
    gov_risk_answers_from_maturity,
    maturidade_para_profundidade,
)
from app.governance.rules.r2_swot import swot_para_checklist
from app.governance.rules.r3_canvas import (
    canvas_para_risco_preliminar,
    opportunity_input_from_canvas_project,
)
from app.governance.rules.r4_evidencias import (
    evidencias_para_sugestao_maturidade,
    load_r4_map,
)


class R1MaturidadeParaProfundidadeTests(unittest.TestCase):
    def test_min_2_is_fundacao(self) -> None:
        out = maturidade_para_profundidade({"GR1": 5, "GR2": 2, "GR3": 4})
        self.assertEqual(out["profundidade"], "fundacao")
        self.assertEqual(out["elo_mais_fraco"], {"question_id": "GR2", "valor": 2})

    def test_min_3_is_intermediario(self) -> None:
        out = maturidade_para_profundidade({"GR1": 5, "GR2": 3, "GR3": 4})
        self.assertEqual(out["profundidade"], "intermediario")

    def test_min_4_is_completo(self) -> None:
        out = maturidade_para_profundidade({"GR1": 5, "GR2": 4, "GR3": 4})
        self.assertEqual(out["profundidade"], "completo")

    def test_min_1_is_fundacao(self) -> None:
        self.assertEqual(maturidade_para_profundidade({"GR1": 1})["profundidade"], "fundacao")

    def test_min_5_is_completo(self) -> None:
        self.assertEqual(maturidade_para_profundidade({"GR1": 5})["profundidade"], "completo")

    def test_rule_id_and_version_in_output(self) -> None:
        out = maturidade_para_profundidade({"GR1": 3})
        self.assertEqual(out["rule_id"], "maturidade_para_profundidade")
        self.assertEqual(out["rule_version"], "1")

    def test_empty_input_raises(self) -> None:
        with self.assertRaises(ValueError):
            maturidade_para_profundidade({})

    def test_filters_only_gov_risk_questions_case_insensitive(self) -> None:
        answers = {"EV1": 5, "DI3": 1, "PC2": 5, "GR1": 4, "gr2": 2}
        self.assertEqual(gov_risk_answers_from_maturity(answers), {"GR1": 4, "gr2": 2})


class R2SwotParaChecklistTests(unittest.TestCase):
    def _swot(self, **overrides) -> dict:
        base = {"forcas": [], "fraquezas": [], "oportunidades": [], "ameacas": []}
        base.update(overrides)
        return base

    def test_selects_fraqueza_by_pilar_governanca(self) -> None:
        swot = self._swot(
            fraquezas=[{"id": "fx_1", "texto": "Sem política de IA", "pilar": "governanca", "impacto": 2}]
        )
        out = swot_para_checklist(swot)
        self.assertEqual(len(out["itens"]), 1)
        item = out["itens"][0]
        self.assertEqual(item["bloco"], "F")
        self.assertEqual(item["item_id"], "F_fx_1")
        self.assertEqual(item["texto"], "Mitigação verificada: Sem política de IA")
        self.assertEqual(item["origem"], {"tipo": "swot", "swot_item_id": "fx_1", "rule": "swot_para_checklist"})

    def test_selects_ameaca_by_gov_risk_question_id(self) -> None:
        swot = self._swot(
            ameacas=[{"id": "a_1", "texto": "Vazamento de dados", "pilar": "", "question_id": "GR2", "impacto": 3}]
        )
        out = swot_para_checklist(swot)
        self.assertEqual(len(out["itens"]), 1)
        self.assertEqual(out["itens"][0]["origem"]["swot_item_id"], "a_1")

    def test_ignores_forca_and_oportunidade_even_if_governanca(self) -> None:
        swot = self._swot(
            forcas=[{"id": "f_1", "texto": "Boa política", "pilar": "governanca", "impacto": 5}],
            oportunidades=[{"id": "o_1", "texto": "Regular cedo", "pilar": "governanca", "impacto": 5}],
        )
        out = swot_para_checklist(swot)
        self.assertEqual(out["itens"], [])

    def test_ignores_item_without_governance_link(self) -> None:
        swot = self._swot(
            fraquezas=[{"id": "fx_2", "texto": "Time pequeno", "pilar": "talento", "question_id": "PC1", "impacto": 5}]
        )
        out = swot_para_checklist(swot)
        self.assertEqual(out["itens"], [])

    def test_critico_when_impacto_at_least_4(self) -> None:
        swot = self._swot(
            fraquezas=[
                {"id": "fx_a", "texto": "A", "pilar": "governanca", "impacto": 4},
                {"id": "fx_b", "texto": "B", "pilar": "governanca", "impacto": 3},
                {"id": "fx_c", "texto": "C", "pilar": "governanca", "impacto": None},
            ]
        )
        out = swot_para_checklist(swot)
        by_id = {i["origem"]["swot_item_id"]: i["critico"] for i in out["itens"]}
        self.assertTrue(by_id["fx_a"])
        self.assertFalse(by_id["fx_b"])
        self.assertFalse(by_id["fx_c"])

    def test_dedupe_on_reexecution_same_item_ids(self) -> None:
        swot = self._swot(
            fraquezas=[{"id": "fx_1", "texto": "X", "pilar": "governanca", "impacto": 5}],
            ameacas=[{"id": "a_1", "texto": "Y", "pilar": "", "question_id": "gr9", "impacto": 2}],
        )
        first = swot_para_checklist(swot)
        second = swot_para_checklist(swot)
        self.assertEqual(
            [i["item_id"] for i in first["itens"]], [i["item_id"] for i in second["itens"]]
        )


class R3CanvasParaRiscoPreliminarTests(unittest.TestCase):
    """Tabela de casos da Seção 9 do prompt original, adaptada à taxonomia real de HITL."""

    def _run(self, sensibilidade, tipo_execucao, hitl, regulatorio) -> str:
        out = canvas_para_risco_preliminar(
            {
                "sensibilidade": sensibilidade,
                "tipo_execucao": tipo_execucao,
                "human_in_the_loop": hitl,
                "regulatorio": regulatorio,
            }
        )
        return out["nivel_preliminar"]

    def test_sensivel_agente_executa_sem_hitl_e_critico(self) -> None:
        self.assertEqual(
            self._run("sensivel", "agente_executa", "nenhum", ["LGPD art.11"]), "critico"
        )

    def test_sensivel_agente_executa_com_hitl_e_alto(self) -> None:
        self.assertEqual(
            self._run("sensivel", "agente_executa", "supervisionar", ["LGPD art.11"]), "alto"
        )

    def test_pessoal_agente_executa_com_hitl_e_alto(self) -> None:
        self.assertEqual(self._run("pessoal", "agente_executa", "aprovar", ["LGPD"]), "alto")

    def test_pessoal_assiste_sugere_e_alto_por_exposicao(self) -> None:
        self.assertEqual(self._run("pessoal", "assiste_sugere", None, ["LGPD"]), "alto")

    def test_interno_assiste_sugere_sem_regulatorio_e_baixo(self) -> None:
        self.assertEqual(self._run("interno", "assiste_sugere", None, []), "baixo")

    def test_interno_agente_executa_com_hitl_e_alto(self) -> None:
        self.assertEqual(self._run("interno", "agente_executa", "sugerir", []), "alto")

    def test_rule_id_and_criterios_in_output(self) -> None:
        out = canvas_para_risco_preliminar(
            {"sensibilidade": "baixo_invalido", "tipo_execucao": "assiste_sugere", "regulatorio": []}
        )
        self.assertEqual(out["rule_id"], "canvas_para_risco_preliminar")
        self.assertEqual(out["rule_version"], "1")
        self.assertIn("criterios", out)
        self.assertEqual(out["sensibilidade_usada"], "interno", "valor invalido cai para interno")

    def test_deriva_sensibilidade_sensivel_de_regulatorio_lgpd_art_11(self) -> None:
        out = canvas_para_risco_preliminar(
            {"regulatorio": ["LGPD art. 11 dados sensíveis"], "tipo_execucao": "assiste_sugere"}
        )
        self.assertEqual(out["sensibilidade_usada"], "sensivel")
        self.assertTrue(out["derivado_de_regulatorio"])

    def test_deriva_sensibilidade_pessoal_de_regulatorio_lgpd_generico(self) -> None:
        out = canvas_para_risco_preliminar({"regulatorio": ["LGPD"], "tipo_execucao": "assiste_sugere"})
        self.assertEqual(out["sensibilidade_usada"], "pessoal")
        self.assertTrue(out["derivado_de_regulatorio"])

    def test_deriva_sensibilidade_interno_sem_regulatorio(self) -> None:
        out = canvas_para_risco_preliminar({"regulatorio": [], "tipo_execucao": "assiste_sugere"})
        self.assertEqual(out["sensibilidade_usada"], "interno")
        self.assertTrue(out["derivado_de_regulatorio"])

    def test_explicit_sensibilidade_not_marked_as_derived(self) -> None:
        out = canvas_para_risco_preliminar(
            {"sensibilidade": "pessoal", "regulatorio": [], "tipo_execucao": "assiste_sugere"}
        )
        self.assertFalse(out["derivado_de_regulatorio"])

    def test_adapter_maps_agente_autonomo_tipo_and_hitl_taxonomy(self) -> None:
        doc = {
            "oportunidade_tipos": ["Agente autônomo"],
            "dados_estruturado": {"sensibilidade": "sensivel"},
            "riscos_estruturado": {"regulatorio": ["LGPD"], "human_in_the_loop": "nenhum"},
        }
        adapted = opportunity_input_from_canvas_project(doc)
        self.assertEqual(adapted["tipo_execucao"], "agente_executa")
        self.assertEqual(adapted["sensibilidade"], "sensivel")
        self.assertEqual(adapted["human_in_the_loop"], "nenhum")

    def test_adapter_defaults_to_assiste_sugere(self) -> None:
        doc = {"oportunidade_tipos": ["Copiloto"], "dados_estruturado": {}, "riscos_estruturado": {}}
        adapted = opportunity_input_from_canvas_project(doc)
        self.assertEqual(adapted["tipo_execucao"], "assiste_sugere")


class R4EvidenciasParaSugestaoMaturidadeTests(unittest.TestCase):
    def test_load_r4_map_reads_real_config(self) -> None:
        rules = load_r4_map()
        self.assertTrue(rules)
        for rule in rules:
            self.assertIn("question_id", rule)
            self.assertTrue(rule.get("tiers"))

    def test_highest_tier_wins_first_match(self) -> None:
        config = [
            {
                "question_id": "GR2",
                "tiers": [
                    {"nota": 5, "conditions": [{"metric": "m", "op": ">=", "value": 0.9}]},
                    {"nota": 3, "conditions": [{"metric": "m", "op": ">=", "value": 0.4}]},
                ],
            }
        ]
        out = evidencias_para_sugestao_maturidade({"m": 0.95}, config)
        self.assertEqual(out["sugestoes"], [{"question_id": "GR2", "nota_sugerida": 5, "evidencia": {"m": 0.95}}])

    def test_falls_through_to_lower_tier(self) -> None:
        config = [
            {
                "question_id": "GR2",
                "tiers": [
                    {"nota": 5, "conditions": [{"metric": "m", "op": ">=", "value": 0.9}]},
                    {"nota": 3, "conditions": [{"metric": "m", "op": ">=", "value": 0.4}]},
                ],
            }
        ]
        out = evidencias_para_sugestao_maturidade({"m": 0.5}, config)
        self.assertEqual(out["sugestoes"][0]["nota_sugerida"], 3)

    def test_no_suggestion_when_no_tier_matches(self) -> None:
        config = [
            {"question_id": "GR2", "tiers": [{"nota": 5, "conditions": [{"metric": "m", "op": ">=", "value": 0.9}]}]}
        ]
        out = evidencias_para_sugestao_maturidade({"m": 0.1}, config)
        self.assertEqual(out["sugestoes"], [])

    def test_missing_metric_does_not_match(self) -> None:
        config = [
            {"question_id": "GR2", "tiers": [{"nota": 5, "conditions": [{"metric": "ausente", "op": ">=", "value": 0.9}]}]}
        ]
        out = evidencias_para_sugestao_maturidade({}, config)
        self.assertEqual(out["sugestoes"], [])

    def test_and_across_multiple_conditions(self) -> None:
        config = [
            {
                "question_id": "GR6",
                "tiers": [
                    {
                        "nota": 5,
                        "conditions": [
                            {"metric": "a", "op": ">=", "value": 0.9},
                            {"metric": "b", "op": "<=", "value": 5},
                        ],
                    }
                ],
            }
        ]
        self.assertEqual(
            evidencias_para_sugestao_maturidade({"a": 0.95, "b": 10}, config)["sugestoes"], []
        )
        self.assertEqual(
            len(evidencias_para_sugestao_maturidade({"a": 0.95, "b": 3}, config)["sugestoes"]), 1
        )

    def test_never_mutates_config_or_payload(self) -> None:
        config = load_r4_map()
        payload = {"pct_sistemas_inventariados": 0.95, "tempo_medio_registro_dias": 0.5}
        config_before = copy.deepcopy(config)
        payload_before = copy.deepcopy(payload)

        evidencias_para_sugestao_maturidade(payload, config)

        self.assertEqual(config, config_before)
        self.assertEqual(payload, payload_before)

    def test_real_config_suggests_gr2_for_strong_inventory_metrics(self) -> None:
        config = load_r4_map()
        payload = {"pct_sistemas_inventariados": 0.95, "tempo_medio_registro_dias": 0.5}
        out = evidencias_para_sugestao_maturidade(payload, config)
        gr2 = next((s for s in out["sugestoes"] if s["question_id"] == "GR2"), None)
        self.assertIsNotNone(gr2)
        self.assertEqual(gr2["nota_sugerida"], 5)

    def test_rule_id_and_version_in_output(self) -> None:
        out = evidencias_para_sugestao_maturidade({}, [])
        self.assertEqual(out["rule_id"], "evidencias_para_sugestao_maturidade")
        self.assertEqual(out["rule_version"], "1")


if __name__ == "__main__":
    unittest.main()
