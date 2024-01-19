# Documentation du Code Monnit

Ce document fournit une documentation complète pour le code Python qui interagit avec l'API Monnit afin de récupérer des données de capteurs. Le code est organisé en sections basées sur des fonctionnalités spécifiques, et chaque section est accompagnée d'exemples pour une meilleure compréhension.

## Initialisation de la Classe Monnit

```python
# Initialise une instance de la classe MonnitAPIManager.
# Charge les paramètres depuis le fichier settings.json
# Initialise les listes pour stocker les capteurs et les données des capteurs.
api = Monnit()
```

### Paramètres de l'Application

Les paramètres de l'application sont lus depuis le fichier **settings.json**. Voici une explication rapide des principaux paramètres :

- `authorization_token`: Jeton d'autorisation pour l'API Monnit.
- `network_id`: Identifiant du réseau Monnit.
- `sensor_list`: Liste d'identifiants de capteurs.
- `start`: Date de début pour la récupération des données des capteurs.
- `end`: Date de fin pour la récupération des données des capteurs.
- `interval_minutes`: Intervalle en minutes entre chaque récupération de données.
- `verbose`: Booléen indiquant si des messages de débogage doivent être affichés.

## Récupération de la Liste des Réseaux

```python
# Récupère la liste des réseaux et stocke les données dans self.network_list.
api.get_network_list()
```

```python
# Affiche la liste des réseaux
print(api.network_list)
```

## Recherche de l'ID du Réseau

```python
# Recherche de l'ID du réseau en fonction de son nom
network_name_to_find = 'Labo-GBZ'
network_id = api.find_network_id(api.network_list, network_name_to_find)
```

## Récupération de la Liste des Capteurs du Réseau

```python
# Récupère la liste des capteurs du réseau sur base d'un identifiant unique et stocke les données dans self.sensor_list.
api.get_sensor_list(network_id=network_id)
```

## Vérification de la Fenêtre Temporelle

```python
# Vérification de la fenêtre temporelle
api.settings['start'] = "2023-12-01 16:30:00"
api.settings['end'] = "2023-12-25 5:00:00"
api.check_for_big_window()
```

## Récupération des Données pour un Capteur Spécifique

```python
# Récupération des données pour un capteur spécifique à intervalles de 10 minutes
onlyonesensor_id = api.sensor_list[0]
api.process_data_for_sensor_id_based_on_window(onlyonesensor_id)
```

Si la fenêtre temporelle est inférieure à sept jours, les données pour un capteur spécifique sont récupérées avec les dates spécifiées.

```python
# Récupération des données pour un capteur spécifique sur une plage temporelle donnée
api.get_data_for_sensor_id(sensor_id=onlyonesensor_id, start="2023-12-12 16:30:00", end="2023-12-15 5:00:00")
```

## Récupération et Traitement des Données de Tous les Capteurs

```python
# Récupération et traitement des données de tous les capteurs en fonction de la fenêtre de temps spécifiée.
an_another_api = Monnit()
an_another_api.run()
```

Cela effectue une récupération de données pour tous les capteurs spécifiés dans `api.sensor_list` avec l'intervalle de temps spécifié dans `api.settings["interval_minutes"]`.