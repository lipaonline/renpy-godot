# Graphe des routes

Généré par `tools/fiches.py graphe`. Formes : rectangle = scène, ovale = fin, double cadre = scène appelée ; pointillés = appel.

```mermaid
flowchart TD
    DEBUT((début)) --> CH01_SC01
    CH01_SC01["CH01_SC01<br/>L'arrivée"]
    CH01_SC02["CH01_SC02<br/>L'appartement de Léna"]
    CH01_SC03A["CH01_SC03A<br/>La confiance"]
    CH01_SC03B["CH01_SC03B<br/>L'interrogatoire"]
    CH01_SC04(["CH01_SC04<br/>Fin de la démo"])
    CH01_SC05(["CH01_SC05<br/>Fin solitaire"])
    CH01_SOUVENIR[["CH01_SOUVENIR<br/>Souvenir du père"]]
    CH01_SC01 -->|"Monter directement"| CH01_SC02
    CH01_SC01 -->|"Regarder la boîte aux lettres"| CH01_SC02
    CH01_SC02 -->|"Lui faire confiance"| CH01_SC03A
    CH01_SC02 -->|"L'interroger sur la photo (si indice_photo)"| CH01_SC03B
    CH01_SC02 -->|"Repartir sous la pluie"| CH01_SC05
    CH01_SC03A --> CH01_SC04
    CH01_SC03B -.->|appel| CH01_SOUVENIR
    CH01_SC03B --> CH01_SC04
```
