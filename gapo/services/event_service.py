import time
from gapo.models.events import GameEvent, EventType, EventPriority, DEFAULT_EVENT_RULES, EventRule
from gapo.models.game_state import GameState
from gapo.core.logging import get_logger
from gapo.core.metrics import active_events
from gapo.core.events import event_bus

logger = get_logger("event_service")


class EventService:
    def __init__(self):
        self.rules: list[EventRule] = DEFAULT_EVENT_RULES.copy()
        self._last_triggered: dict[EventType, float] = {}
        self._custom_rules: list[EventRule] = []

    def add_rule(self, rule: EventRule) -> None:
        self._custom_rules.append(rule)

    def remove_rule(self, event_type: EventType) -> None:
        self._custom_rules = [r for r in self._custom_rules if r.event_type != event_type]

    def check_events(self, game_state: GameState) -> list[GameEvent]:
        events = []
        current_time = time.time()

        for rule in self.rules + self._custom_rules:
            if self._is_on_cooldown(rule.event_type, current_time, rule.cooldown):
                continue

            if self._evaluate_condition(rule, game_state):
                event = self._create_event(rule, game_state)
                events.append(event)
                self._last_triggered[rule.event_type] = current_time
                active_events.labels(event_type=rule.event_type.value).inc()

                event_bus.publish_sync("game_event", event)

        return events

    def _is_on_cooldown(self, event_type: EventType, current_time: float, cooldown: float) -> bool:
        last = self._last_triggered.get(event_type, 0)
        return current_time - last < cooldown

    def _evaluate_condition(self, rule: EventRule, state: GameState) -> bool:
        condition = rule.condition.lower()

        if "enemy_missing" in condition:
            return self._check_enemy_missing(state, condition)

        if "dragon_spawning" in condition or "baron_spawning" in condition:
            return self._check_objective_spawning(state, condition)

        if "multiple_hp_dropping" in condition:
            return self._check_fight_started(state)

        if "player_alone_enemy_side" in condition:
            return self._check_positioning_error(state)

        if "wave_under_turret" in condition:
            return self._check_wave_management(state)

        if "level ==" in condition or "mythic_completed" in condition:
            return self._check_powerspike(state, condition)

        if "flash_used" in condition or "ignite_used" in condition or "heal_used" in condition:
            return self._check_summoner_used(state, condition)

        return False

    def _check_enemy_missing(self, state: GameState, condition: str) -> bool:
        missing_threshold = 10
        if ">" in condition:
            try:
                missing_threshold = int(condition.split(">")[1].split("s")[0].strip())
            except (IndexError, ValueError):
                pass

        for enemy in state.enemies.values():
            if not enemy.is_visible:
                missing_time = (state.timestamp - enemy.last_seen).total_seconds()
                if missing_time > missing_threshold:
                    return True
        return False

    def _check_objective_spawning(self, state: GameState, condition: str) -> bool:
        if "dragon_spawning" in condition:
            timer = state.minimap.dragon_timer
            if timer is not None and timer <= 10 and timer > 0:
                enemies_near = len(state.minimap.enemies)
                return enemies_near > 0
        if "baron_spawning" in condition:
            timer = state.minimap.baron_timer
            if timer is not None and timer <= 15 and timer > 0:
                enemies_near = len(state.minimap.enemies)
                return enemies_near > 0
        return False

    def _check_fight_started(self, state: GameState) -> bool:
        hp_dropping = 0
        for player in [state.player] + list(state.allies.values()) + list(state.enemies.values()):
            if player.max_hp > 0:
                hp_pct = player.hp / player.max_hp
                if hp_pct < 0.8:
                    hp_dropping += 1
        return hp_dropping >= 3

    def _check_positioning_error(self, state: GameState) -> bool:
        if state.player.position_x == 0 and state.player.position_y == 0:
            return False

        enemies_visible = sum(1 for e in state.enemies.values() if e.is_visible)
        if enemies_visible == 0:
            return True

        return False

    def _check_wave_management(self, state: GameState) -> bool:
        return False

    def _check_powerspike(self, state: GameState, condition: str) -> bool:
        if "level ==" in condition:
            try:
                level = int(condition.split("==")[1].split()[0])
                return state.player.level == level
            except (IndexError, ValueError):
                pass

        if "mythic_completed" in condition:
            mythic_items = ["stridebreaker", "divine sunderer", "goredrinker", "liandry", "everfrost", "moonstone"]
            return any(item.lower() in mythic_items for item in state.player.items)

        return False

    def _check_summoner_used(self, state: GameState, condition: str) -> bool:
        return False

    def _create_event(self, rule: EventRule, state: GameState) -> GameEvent:
        message = rule.message_template
        message = message.replace("{champion}", state.player.champion)
        message = message.replace("{lane}", "sua lane")
        message = message.replace("{missing_time}", "10")
        message = message.replace("{objective}", "Dragão")
        message = message.replace("{timer}", "5")
        message = message.replace("{enemy_count}", "2")
        message = message.replace("{location}", "rio")
        message = message.replace("{target_priority}", "o carry inimigo")
        message = message.replace("{time}", "15")
        message = message.replace("{detail}", f"Level {state.player.level}")
        message = message.replace("{enemy}", "Inimigo")
        message = message.replace("{spell}", "Flash")
        message = message.replace("{cd}", "300")

        return GameEvent(
            event_type=rule.event_type,
            priority=rule.priority,
            message=message,
            context=state.to_context_dict(),
            champion_involved=state.player.champion,
            cooldown_seconds=rule.cooldown,
        )