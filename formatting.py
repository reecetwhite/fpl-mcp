from cache import Element, Fixture, FPLCache, Team


def format_player(p: Element, cache: FPLCache) -> str:
    team = cache.get_team(p["team"])
    team_name = team["short_name"] if team else "Unknown"
    pos = cache.get_position_name(p["element_type"])
    price = p["now_cost"] / 10
    element_type = p["element_type"]

    # Base stats for all positions
    parts = [
        f"{p['web_name']} ({team_name} {pos}) £{price}m",
        f"{p['total_points']}pts ({p['points_per_game']}/g)",
        f"form:{p['form']}",
        f"{p['selected_by_percent']}%",
        f"{p['minutes']}min",
        f"{p['goals_scored']}g {p['assists']}a {p['bonus']}bps",
    ]

    # Position-specific stats
    if element_type == 1:  # GKP
        parts.append(f"{p['saves']}sv {p['clean_sheets']}cs")
    elif element_type == 2:  # DEF
        parts.append(f"{p['clean_sheets']}cs {p['goals_conceded']}gc | xG:{p['expected_goals']} xA:{p['expected_assists']} | def/90:{p['defensive_contribution_per_90']}")
    elif element_type == 3:  # MID
        parts.append(f"xG:{p['expected_goals']} xA:{p['expected_assists']} | {p['clean_sheets']}cs | def/90:{p['defensive_contribution_per_90']}")
    else:  # FWD
        parts.append(f"xG:{p['expected_goals']} xA:{p['expected_assists']}")

    # Cards if any
    if p["yellow_cards"] or p["red_cards"]:
        parts.append(f"{p['yellow_cards']}Y {p['red_cards']}R")

    # Availability flag if not available
    if p["status"] != "a":
        status_map = {"d": "doubtful", "i": "injured", "n": "unavailable", "s": "suspended", "u": "unavailable"}
        status_text = status_map.get(p["status"], p["status"])
        chance = p.get("chance_of_playing_next_round")
        chance_str = f" {chance}%" if chance is not None else ""
        news = p.get("news", "")
        news_str = f" - {news}" if news else ""
        parts.append(f"⚠️ {status_text}{chance_str}{news_str}")

    return " | ".join(parts)


def format_team(t: Team) -> str:
    return (
        f"{t['name']} ({t['short_name']}) | strength: {t['strength']} | "
        f"home: {t['strength_overall_home']} atk:{t['strength_attack_home']} def:{t['strength_defence_home']} | "
        f"away: {t['strength_overall_away']} atk:{t['strength_attack_away']} def:{t['strength_defence_away']}"
    )


def format_fixture(fix: Fixture, cache: FPLCache, team_perspective: int | None = None) -> str:
    """Format fixture. If team_perspective given, show opponent with H/A and FDR."""
    home = cache.get_team(fix["team_h"])
    away = cache.get_team(fix["team_a"])
    home_name = home["short_name"] if home else "???"
    away_name = away["short_name"] if away else "???"

    event = fix.get("event")
    gw = f"GW{event}" if event else "TBD"

    kickoff = fix.get("kickoff_time")
    if kickoff:
        # Parse ISO format and format nicely
        dt = kickoff.replace("T", " ")[:16]  # "2024-01-25 15:00"
    else:
        dt = "TBD"

    if fix["finished"] and fix["team_h_score"] is not None:
        score = f"{fix['team_h_score']}-{fix['team_a_score']}"
    else:
        score = None

    if team_perspective:
        if team_perspective == fix["team_h"]:
            opp = away_name
            venue = "H"
            fdr = fix["team_h_difficulty"]
        else:
            opp = home_name
            venue = "A"
            fdr = fix["team_a_difficulty"]

        if score:
            return f"{gw}: {opp} ({venue}) FDR:{fdr} | {score} | {dt}"
        return f"{gw}: {opp} ({venue}) FDR:{fdr} | {dt}"

    # Neutral format
    if score:
        return f"{gw}: {home_name} {score} {away_name} | {dt}"
    return f"{gw}: {home_name} vs {away_name} | {dt}"
