#!/usr/bin/env python3
"""Script pour ajouter les compétitions U14 au fetchData de App.jsx"""

# Lire le fichier
with open('Dashboard/src/App.jsx', 'r') as f:
    content = f.read()

# Ajouter les conditions pour U14 après carquefou-sd
OLD_CODE = '''      } else if (competitionId === 'carquefou-sd') {
        promises.push(axios.get(`${API_BASE}/carquefou/sd/matchs`));
      }'''

NEW_CODE = '''      } else if (competitionId === 'carquefou-sd') {
        promises.push(axios.get(`${API_BASE}/carquefou/sd/matchs`));
      } else if (competitionId === 'interligues-u14-garcons') {
        promises.push(axios.get(`${API_BASE}/interligues-u14-garcons/matchs`));
      } else if (competitionId === 'interligues-u14-filles') {
        promises.push(axios.get(`${API_BASE}/interligues-u14-filles/matchs`));
      }'''

content = content.replace(OLD_CODE, NEW_CODE)

# Ajouter les traitements pour U14 après carquefou-sd
OLD_RESULT = '''      if (competitionId === 'carquefou-sd') {
        setMatchs(results[0].data.data);
      } else {
        setClassement(results[0].data.data);
        setMatchs(results[1].data.data);
      }'''

NEW_RESULT = '''      if (competitionId === 'carquefou-sd' || competitionId === 'interligues-u14-garcons' || competitionId === 'interligues-u14-filles') {
        setMatchs(results[0].data.data);
      } else {
        setClassement(results[0].data.data);
        setMatchs(results[1].data.data);
      }'''

content = content.replace(OLD_RESULT, NEW_RESULT)

# Modifier la condition du tab Classement
OLD_TAB = '''              {selectedCompetition !== 'carquefou-sd' && ('''

NEW_TAB = '''              {selectedCompetition !== 'carquefou-sd' && selectedCompetition !== 'interligues-u14-garcons' && selectedCompetition !== 'interligues-u14-filles' && ('''

content = content.replace(OLD_TAB, NEW_TAB)

# Écrire le fichier
with open('Dashboard/src/App.jsx', 'w') as f:
    f.write(content)

print("✅ Compétitions U14 ajoutées au fetchData de App.jsx!")
