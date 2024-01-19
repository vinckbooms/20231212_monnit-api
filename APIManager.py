import requests
import json
import pandas as pd
import time
import pytz
import os
import sys
from datetime import datetime, timedelta
from tqdm import tqdm
from typing import List, Optional
from colorama import Fore, Style, init

class Monnit:
    """
    Cette classe gère l'interaction avec l'API Monnit pour récupérer la liste des capteurs et les données associées.
    """

    def __init__(self):
        """
        Initialise une instance de la classe MonnitAPIManager.

        Charge les paramètres depuis le fichier settings.json et initialise les listes pour stocker les capteurs
        et les données des capteurs.
        """

        # Chargement des paramètres depuis le fichier settings.json
        self.handle_settings_file()

        # Création d'un interrupteur pour un intervalle > à 7 jours
        self.big_window = False
        self.interval_seconds = self.settings["interval_minutes"] * 60

    def log(self, message:str):
        """
        Imprime un message et enregistre dans un fichier de journal si le mode verbeux est activé dans les paramètres.

        Parameters:
            message (str): Message à imprimer et enregistrer avec des codes d'échappement ANSI.
        """

        if self.settings.get('verbose'):
            print(message)

        if self.settings.get('log_to_file'):
            log_file_path = "log.txt"
            try:
                with open(log_file_path, 'a', encoding='utf-8') as log_file:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cleaned_message = self.strip_ansi(message)
                    log_file.write(f"{timestamp} | {cleaned_message}\n")
            except Exception as e:
                print(f"{Fore.YELLOW}Avertissement :{Style.RESET_ALL} Erreur lors de l'écriture dans le fichier journal, {e}")

    def handle_settings_file(self):
        """
        Charge les paramètres depuis le fichier settings.json et gère les erreurs éventuelles.

        Raises:
            FileNotFoundError: Si le fichier settings.json n'est pas trouvé.
            JSONDecodeError: Si le fichier settings.json a un format JSON incorrect.
        """
        print("Exécution de la méthode handle_settings_file()")
        try:
            with open("settings.json", encoding="utf-8") as file:
                self.settings = json.load(file)

            self.sensor_list = self.settings["sensor_list"]
            self.log(f"{Fore.GREEN}[INFOS] {Style.RESET_ALL}Paramètres chargés avec succès: {self.settings}")

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"{Fore.RED}[ERREUR] {Style.RESET_ALL}Erreur lors de la lecture du fichier de paramètres, {e}")
            sys.exit(1)

    def strip_ansi(self, text):
        # Fonction pour supprimer les codes ANSI de Colorama
        from re import sub
        return sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)

    def convert_timestamp_to_datetime(self, timestamp: int):
        """
        Convertit un timestamp Unix en objet datetime avec le fuseau horaire de Bruxelles.

        Parameters:
            timestamp (int): Timestamp Unix.

        Returns:
            str: Date et heure formatées au format 'YYYY-MM-DD HH:mm:ss'.
        """
        # self.log("Exécution de la méthode convert_timestamp_to_datetime()")
        try:
            timestamp = int(timestamp[6:-2]) / 1000
            utc_datetime = pd.to_datetime(timestamp, unit='s', utc=True)
            
            # Définir le fuseau horaire pour Bruxelles (GMT+2)
            brussels_timezone = pytz.timezone('Europe/Brussels')
            
            # Convertir en heure locale de Bruxelles
            brussels_datetime = utc_datetime.tz_convert(brussels_timezone)
        
            # Return au format 'YYYY-MM-DD HH:mm:ss'
            return brussels_datetime.strftime('%Y-%m-%d %H:%M:%S')

        except Exception as e:

            self.log(f"{Fore.RED}[ERREUR] {Style.RESET_ALL} lors de la conversion du timestamp en datetime : {e}")
            return None
    
    def check_for_big_window(self):
        """
        Vérifie si l'intervalle entre start et end est inférieur à une semaine.
        Si non, divise l'intervalle en tranches d'une semaine et stocke les résultats dans self.cover_ranges.
        """
        self.log("Exécution de la méthode check_for_big_window()")
        start_date = datetime.strptime(self.settings['start'], '%Y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(self.settings['end'], '%Y-%m-%d %H:%M:%S')

        # Déterminer la différence entre les deux dates
        date_difference = end_date - start_date

        # Vérifier si l'intervalle est inférieur à une semaine
        if date_difference > timedelta(weeks=1):
            self.big_window = True
            self.log(f"{Fore.YELLOW}[AVERTISSEMENT] {Style.RESET_ALL} Fenêtre suppérieur à sept jour détectée")
            self.cover_ranges=[]

            # Diviser l'intervalle en tranches d'une semaine
            self.cover_ranges = []
            current_start = start_date
            while current_start < end_date:
                current_end = current_start + timedelta(weeks=1)
                if current_end > end_date:
                    current_end = end_date
                self.cover_ranges.append((current_start.strftime('%Y-%m-%d %H:%M:%S'), current_end.strftime('%Y-%m-%d %H:%M:%S')))
                current_start = current_end

            # Utiliser la première tranche comme nouvel intervalle
            self.settings['start'], self.settings['end'] =  self.cover_ranges[0]
            self.log(f"L'intervalle initial a été ajusté en tranches d'une semaine : {self.cover_ranges}")
        else:
            self.log(f"L'intervale {date_difference} est < à {timedelta(weeks=1)}")

    def progressbar(self, interval_seconds=600, title: str="Délai imposé"):
        """
        Affiche une barre de progression avec un intervalle spécifié entre les itérations.

        Parameters:
            interval_seconds (int): Intervalle de sommeil entre chaque itération en secondes. Par défaut, 600 secondes (10 minutes).
            title (str): Titre de la barre de progression.
        """
        # self.log("Exécution de la méthode progressbar()")
        # Pour 600 secondes, avec une itération toutes les 10 secondes
        iterable = range(interval_seconds // 10)  

        for _ in tqdm(iterable, desc=title, unit="s"):
             # Pause de 10 secondes entre les itérations
            time.sleep(10) 

    def get_network_list(self):
        """
        Récupère la liste des réseaux et stocke les données dans self.network_list.

        Parameters:
            verbose (bool): Indique si les messages de débogage doivent être affichés. Par défaut, True.
        """
        self.log("Exécution de la méthode get_network_list()")
        # Initialisation de la liste pour stocker les réseaux
        self.network_list = []

        # Construction de la requête pour obtenir la liste des réseaux
        formatted_request = f'https://www.imonnit.com/json/NetworkList/{self.settings["authorization_token"]}?'
        self.log(f"{Fore.GREEN}[INFOS] {Style.RESET_ALL}Envoi de la requête : {formatted_request}")

        # Envoi de la requête et récupération de la réponse
        try:
            response = requests.get(formatted_request)
            response.raise_for_status()
            answer_in_json = response.json()

            # Extraction de la liste des réseaux et stockage dans self.network_list
            self.network_list = answer_in_json.get('Result', [])
            self.network_list = [{"NetworkID": net["NetworkID"], "NetworkName": net["NetworkName"]} for net in self.network_list]
            self.log(f"Liste des réseaux présents : {self.network_list}")

        except requests.RequestException as e:
            self.log(f"{Fore.RED}[ERREUR] {Style.RESET_ALL}Erreur lors de la récupération de la liste des réseaux : {e}")

    def find_network_id(self, network_list: List[dict], network_name:str):
        """
        Trouve l'ID du réseau en fonction du nom.

        Parameters:
            network_list (list): Liste des réseaux sous forme de dictionnaires.
            network_name (str): Nom du réseau à rechercher.

        Returns:
            int or None: L'ID du réseau si trouvé, sinon None.
        """
        self.log("Exécution de la méthode find_network_id()")
        for network in network_list:
            if network["NetworkName"] == network_name:
                self.log(f"L'ID du réseau '{network_name}' est : {network['NetworkID']}")
                return network["NetworkID"]

        self.log(f"{Fore.RED}[ERREUR] {Style.RESET_ALL}Le réseau '{network_name}' n'a pas été trouvé.")

        return None

    def get_sensor_list(self, network_id:int):
        """
        Récupère la liste des capteurs du réseau et stocke les données dans self.sensor_list.

        Parameters:
            network_id (int): L'ID du réseau.
        """
        self.log("Exécution de la méthode get_sensor_list()")

        # Initialisation des listes pour stocker les capteurs
        self.sensor_list = []
        
        # Construction de la requête pour obtenir la liste des capteurs
        formatted_request = f'https://www.imonnit.com/json/SensorList/{self.settings["authorization_token"]}?NetworkID={network_id}'
        self.log(f"Envoi de la requête : {formatted_request}")

        # Envoi de la requête et récupération de la réponse
        try:
            response = requests.get(formatted_request)
            response.raise_for_status()
            answer_in_json = response.json()

            # Extraction de la liste des capteurs et stockage dans self.sensor_list
            self.sensor_list = [sensor['SensorID'] for sensor in answer_in_json.get('Result', [])]
            self.log(f"Liste des capteurs présent dans le network:{self.sensor_list}")

        except requests.RequestException as e:
            self.log(f"{Fore.RED}[ERREUR] {Style.RESET_ALL} lors de la récupération de la liste des capteurs : {e}")

    def get_data_for_sensor_id(self, sensor_id: int, start: str, end: str):
        """
        Récupère les données d'un capteur spécifique dans une plage de dates et exporte les données dans un fichier CSV.

        Parameters:
            sensor_id (int): L'ID du capteur.
            start (str): Date de début au format 'YYYY-MM-DD HH:mm:ss'.
            end (str): Date de fin au format 'YYYY-MM-DD HH:mm:ss'.
        """
        self.log("Exécution de la méthode get_data_for_sensor_id()")
 
        # Construction de la requête pour obtenir les données du capteur dans la plage de dates spécifiée
        formatted_request = f'https://www.imonnit.com/json/SensorDataMessages/{self.settings["authorization_token"]}?sensorID={sensor_id}&fromDate={start}&toDate={end}'
        self.log(f"Envoi de la requête : {formatted_request}")

        # Envoi de la requête et récupération de la réponse
        try: 
            response  = requests.get(formatted_request)
            response.raise_for_status()

            answer_in_json = response.json()
            result = answer_in_json.get('Result')

            # Création d'un DataFrame avec les résultats
            self.df = pd.DataFrame(result)

            # Vérifier si le DataFrame n'est pas vide
            if not self.df.empty:
                # Appliquer la fonction à la colonne MessageDate
                self.df['MessageDate'] = self.df['MessageDate'].apply(self.convert_timestamp_to_datetime)
                self.df['MessageDate'] = pd.to_datetime(self.df['MessageDate'])
                self.df['MessageDate'] = self.df['MessageDate'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # Exportation du DataFrame vers un fichier CSV
                fichier_csv = os.path.join("output", f"{start.split(' ')[0].replace('-', '')}_{end.split(' ')[0].replace('-', '')}_{sensor_id}.csv")
                self.df.to_csv(fichier_csv, index=False)

                self.log(f"{Fore.GREEN}[SUCCESS] {Style.RESET_ALL}Le fichier CSV '{fichier_csv}' a été créé avec succès.")
            else:
                self.log(f"{Fore.RED}[ERREUR] {Style.RESET_ALL}La requête a renvoyé une réponse vide.")
            
            # Attente imposée
            self.progressbar(self.interval_seconds)

        except requests.RequestException as e:
            self.log(f"{Fore.RED}[ERREUR]: {Style.RESET_ALL}Erreur lors de la récupération des données pour le capteur {sensor_id} : {e}")

    def get_data_for_sensor_list(self, start: str, end: str):
        """
        Récupère les données pour chaque capteur à intervalles de 10 minutes.

        Parameters:
            start_date (str): Date de début au format 'YYYY-MM-DD HH:mm:ss'.
            end_date (str): Date de fin au format 'YYYY-MM-DD HH:mm:ss'.
        """
        self.log("Exécution de la méthode get_data_for_sensor_list()")
        # Obtient la liste des capteurs
        sensor_list = self.sensor_list

        for sensor_id in sensor_list:
            # Exécute GetDataFromSensorID pour chaque capteur
            self.get_data_for_sensor_id(sensor_id, start, end)

    def process_data_for_sensor_id_based_on_window(self, sensor_id: int):
        """
        Récupère et traite les données d'un capteur spécifique en fonction de la fenêtre de temps spécifiée.

        Parameters:
            sensor_id: int

        """
        self.log("Exécution de la méthode process_data_for_sensor_id_based_on_window()")
        if self.big_window:
            for cover_range in self.cover_ranges:
                range_start = cover_range[0]
                range_end = cover_range[1]

                self.log(f"{Fore.GREEN}[INFOS] {Style.RESET_ALL}Traitement de la plage de dates de {range_start} à {range_end}")
                self.get_data_for_sensor_id(sensor_id, range_start, range_end)
        else:
            self.get_data_for_sensor_id(sensor_id, self.settings['start'] , self.settings['end'])

    def process_data_for_sensor_list_based_on_window(self):
        """
        Récupère et traite les données de tous les capteurs en fonction de la fenêtre de temps spécifiée.
        """
        self.log("Exécution de la méthode process_data_for_sensor_list_based_on_window()")
        if self.big_window:
            for cover_range in self.cover_ranges:
                range_start = cover_range[0]
                range_end = cover_range[1]
                self.log(f"{Fore.GREEN}[INFOS] {Style.RESET_ALL}Traitement de la plage de dates de {range_start} à {range_end}")
                self.get_data_for_sensor_list(range_start, range_end)
        else:
            self.get_data_for_sensor_list(self.settings['start'] , self.settings['end'])

    def run(self):
        """
        Exécute les étapes nécessaires pour récupérer et traiter les données des capteurs.
        Sur base des paramètres par défauts dans settings.json
        """
        self.log("Exécution de la méthode run()")
        self.check_for_big_window()
        self.process_data_for_sensor_list_based_on_window()

if __name__ == "__main__":
    api = Monnit()

    # Exécution simple (basé sur les infos de settings.json): 
    # api.run()

    # Exécution explosée/spécifique (récupération des infos sur le serveur)
    # étape par étape
    # Choix d'un réseau existant à partir des réseaux existant dans api.network_list.
    # Sinon la ligne est commenté -> récupération de la liste de settings.json
    api.get_network_list()

    # Obtention de L'id unique du réseau
    network_name_to_find = 'Labo-GBZ'
    network_id = api.find_network_id(api.network_list, network_name_to_find)

    # Récupère la liste des capteurs appartenant aux network_id
    api.get_sensor_list(network_id)

    # Changement des valeurs de début et de fin par défaut et vérification des fenêtre < à 7 jours 
    api.settings['start'] = "2023-12-01 16:30:00"
    api.settings['end'] = "2023-12-25 5:00:00"
    api.check_for_big_window()

    # Exécution pour récupérer les des données de tous le réseau spécifié dans api.network_list
    api.process_data_for_sensor_list_based_on_window()

    # Exécution pour obtenir juste les données d'un capteur
    sensor_id=345749

    api.process_data_for_sensor_id_based_on_window(sensor_id)


