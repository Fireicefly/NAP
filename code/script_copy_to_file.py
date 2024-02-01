import os
import shutil
import time

def get_number_file(nom_fichier):
    if nom_fichier in correct_files:
        return int(nom_fichier[1:2])
    else:
        return None

def compare_and_paste(dossier_source, dossier_destination):
    noms_fichiers = os.listdir(os.path.join(os.getcwd(), dossier_destination))
    for nom_fichier in noms_fichiers:
        numero_fichier = get_number_file(nom_fichier)
        print(nom_fichier, numero_fichier)
        if numero_fichier is not None:
            chemin_fichier_source = os.path.join(dossier_source, nom_fichier)
            chemin_fichier_destination = os.path.join(dossier_destination, f"i{numero_fichier}_startupconfig.cfg")

            try:
                if os.path.exists(chemin_fichier_destination):
                    os.remove(chemin_fichier_destination)
                shutil.copy2(chemin_fichier_source, dossier_destination)
                print(f"Le fichier {nom_fichier} a été déplacé vers {dossier_destination}")
            except FileNotFoundError:
                print(f"Le fichier {nom_fichier} n'existe pas.")
            except PermissionError:
                print(f"Vous n'avez pas la permission de déplacer le fichier {nom_fichier}.")


start = time.time()

path_correct_files = os.path.join(os.getcwd())
correct_files = os.listdir(path_correct_files)

# Dossier GNS3
path_dossier_principal = r"c:\Users\Portable\GNS3\projects\gns3_avec_python\project-files\dynamips"
dossiers = os.listdir(path_dossier_principal)

for nom_dossier in dossiers:
    path_dossier_destination = os.path.join(path_dossier_principal, nom_dossier, "configs")
    if os.path.exists(path_dossier_destination):
        compare_and_paste(path_correct_files, path_dossier_destination)

end = time.time()
print("temps d'execution :", end-start)