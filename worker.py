import requests
from datetime import date
import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']

conn = psycopg2.connect(DATABASE_URL)


def find_matches():
    cursor = conn.cursor()

    # Создаем таблицу для хранения данных о матчах (если она не существует)
    cursor.execute('''CREATE TABLE IF NOT EXISTS fixtures
                      (id SERIAL PRIMARY KEY, home_team VARCHAR(255), away_team VARCHAR(255), fixture_id INTEGER, league_id INTEGER)''')

    # Список интересующих лиг
    leagues = ["235", "123"]

    # Дата сегодняшнего дня
    today = date.today().strftime("%Y-%m-%d")

    for league_id in leagues:
        url = "https://v3.football.api-sports.io/fixtures"
        querystring = {
            "league": league_id,
            "season": "2023",
            "date": today
        }
        headers = {
            'x-apisports-key': "d687e02afc3ddcaf9299988a94faf74f"
        }

        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()

        for fixture in data['response']:
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            fixture_id = fixture['fixture']['id']

            # Записываем данные в таблицу, если такой записи еще нет
            cursor.execute(
                "SELECT COUNT(*) FROM fixtures WHERE home_team = %s AND away_team = %s AND fixture_id = %s AND league_id = %s",
                (home_team, away_team, fixture_id, league_id))
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute(
                    "INSERT INTO fixtures (home_team, away_team, fixture_id, league_id) VALUES (%s, %s, %s, %s)",
                    (home_team, away_team, fixture_id, league_id))
                conn.commit()

    # Закрываем соединение с базой данных
    cursor.close()
    conn.close()

    return 1


def get_matches():
    cursor = conn.cursor()

    # Извлекаем данные о матчах из базы данных
    cursor.execute("SELECT home_team, away_team, fixture_id FROM fixtures")
    matches = cursor.fetchall()

    # Закрываем соединение с базой данных
    cursor.close()
    conn.close()

    # Если матчей нет, отправляем сообщение об этом
    if not matches:
        return None
    else:
        return matches


def get_match_data(home_team, away_team, fixture_id):
    url = "https://v3.football.api-sports.io/predictions"
    querystring = {
        "fixture": fixture_id  # Здесь нужно указать ID матча
    }
    headers = {
        'x-apisports-key': "d687e02afc3ddcaf9299988a94faf74f"
    }

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    match_data = ""

    for prediction in data['response']:
        advice = prediction["predictions"]['advice']
        home_team_percent = prediction["predictions"]['percent']['home']
        home_team_last_5_avg_goals = prediction['teams']['home']['last_5']['goals']['for']['average']
        home_team_last_5_against_avg_goals = prediction['teams']['home']['last_5']['goals']['against']['average']

        away_team_percent = prediction["predictions"]['percent']['away']
        away_team_last_5_avg_goals = prediction['teams']['away']['last_5']['goals']['for']['average']
        away_team_last_5_against_avg_goals = prediction['teams']['away']['last_5']['goals']['against']['average']

        draw_percent = prediction["predictions"]['percent']['draw']

        match_data += f"Прогноз: {advice}\n"
        match_data += f"{home_team} вероятность: {home_team_percent}\n"
        match_data += f"Ничья вероятность: {draw_percent}\n"
        match_data += f"{away_team} вероятность: {away_team_percent}\n"

        match_data += f"Последние 5 игр (ср.):\n" \
                      f"Голы: {home_team_last_5_avg_goals} - {away_team_last_5_avg_goals}\n" \
                      f"Пропущено: {home_team_last_5_against_avg_goals} - {away_team_last_5_against_avg_goals}\n"

        home_team_yellow_cards_season = 0
        away_team_yellow_cards_season = 0

        home_team_matches_count = 0
        away_team_matches_count = 0

        for time in ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '91-105']:
            if prediction['teams']['home']['league']['cards']['yellow'][time]['total'] is not None:
                home_team_matches_count = len(prediction['teams']['home']['league']['form'])
                home_team_yellow_cards_season += prediction['teams']['home']['league']['cards']['yellow'][time]['total']
            if prediction['teams']['away']['league']['cards']['yellow'][time]['total'] is not None:
                away_team_matches_count = len(prediction['teams']['away']['league']['form'])
                away_team_yellow_cards_season += prediction['teams']['away']['league']['cards']['yellow'][time]['total']

        if home_team_matches_count > 0:
            if home_team_yellow_cards_season / home_team_matches_count:
                match_data += f'Карточки (сред.)\n' \
                              f'{home_team}: {round(home_team_yellow_cards_season / home_team_matches_count, 2)}\n'

        if away_team_matches_count > 0:
            if away_team_yellow_cards_season / away_team_matches_count:
                match_data += f'Карточки (сред.)\n' \
                              f'{away_team}: {round(away_team_yellow_cards_season / away_team_matches_count, 2)}\n'

        home_team_h2h_precents = prediction['comparison']['h2h']['home']
        away_team_h2h_precents = prediction['comparison']['h2h']['away']

        match_data += f"H2H: {home_team} {home_team_h2h_precents} - {away_team_h2h_precents} {away_team}\n"

    return match_data


def get_odds(fixture_id):
    url = "https://v3.football.api-sports.io/odds"
    querystring = {
        "fixture": fixture_id,
        "bookmaker": "11"
    }
    headers = {
        'x-apisports-key': "d687e02afc3ddcaf9299988a94faf74f"
    }

    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    message = ""

    for odd in data['response']:
        for bookmaker in odd['bookmakers']:
            if bookmaker['name'] == '1xBet':
                for bet in bookmaker['bets']:
                    if bet['name'] == 'Home Team Yellow Cards':
                        for value in bet['values']:
                            num_odd = float(value['odd'])
                            if 1.3 <= num_odd <= 2.2:
                                bet_type, bet_indx = value['value'].split(' ')
                                if int(bet_indx[-1]) == 5 and len(bet_indx) == 3:
                                    message += f"Тотал 1 команды: {bet_type} {bet_indx} за {num_odd}\n"

                    elif bet['name'] == 'Away Team Yellow Cards':
                        for value in bet['values']:
                            num_odd = float(value['odd'])
                            if 1.3 <= num_odd <= 2.2:
                                bet_type, bet_indx = value['value'].split(' ')
                                if int(bet_indx[-1]) == 5 and len(bet_indx) == 3:
                                    message += f"Тотал 2 команды: {bet_type} {bet_indx} за {num_odd}\n"

                    elif bet['name'] == 'Yellow Over/Under':
                        for value in bet['values']:
                            num_odd = float(value['odd'])
                            if 1.3 <= num_odd <= 2.2:
                                bet_type, bet_indx = value['value'].split(' ')
                                if int(bet_indx[-1]) == 5 and len(bet_indx) == 3:
                                    message += f"Общий Тотал: {bet_type} {bet_indx} за {num_odd}\n"

                    elif bet['name'] == 'Yellow Cards 1x2':
                        for value in bet['values']:
                            num_odd = float(value['odd'])
                            if 1.1 <= num_odd:
                                bet_type = value['value']
                                if bet_type != "Draw":
                                    message += f"Cards 1x2: {bet_type} за {num_odd}\n"

    return message
