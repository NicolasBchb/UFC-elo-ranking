# %%
from elo import Elo, Rating
import pandas as pd
from tqdm import tqdm
import dtale


# %%
elo_env = Elo(initial=1200, k_factor=50, rating_class=int)

df_fights = pd.read_csv("data/fights.csv", sep=";").sort_values("eventDate")

# df_fights = df_fights[df_fights["weightClass"] == "Lightweight"]

df_roster = (
    pd.concat(
        [
            df_fights[["winnerHref", "winnerFirstName", "winnerLastName"]].rename(
                columns={
                    "winnerHref": "href",
                    "winnerFirstName": "firstName",
                    "winnerLastName": "lastName",
                }
            ),
            df_fights[["loserHref", "loserFirstName", "loserLastName"]].rename(
                columns={
                    "loserHref": "href",
                    "loserFirstName": "firstName",
                    "loserLastName": "lastName",
                }
            ),
        ]
    )
    .drop_duplicates()
    .reset_index(drop=True)
)

fighters = df_roster["href"].unique().tolist()

# %%
fighters_dict = {}
for fighter in tqdm(
    fighters, desc="Initializing ratings", unit="fighter", total=len(fighters)
):
    fighters_dict[fighter] = elo_env.create_rating()

# %%
for index, row in tqdm(
    df_fights.iterrows(), desc="Rating fights", unit="fight", total=len(df_fights)
):
    winner = row["winnerHref"]
    loser = row["loserHref"]
    fighters_dict[winner], fighters_dict[loser] = elo_env.rate_1vs1(
        fighters_dict[winner], 
        fighters_dict[loser], 
        drawn=row["result"] == "draw"
    )

# %%
df_elos = (
    pd.DataFrame.from_dict(fighters_dict, orient="index", columns=["elo"])
    .reset_index()
    .rename(columns={"index": "href"})
)
df_elos = df_roster.merge(df_elos, on="href", how="left").fillna(1500).sort_values("elo", ascending=False)

df_elos.to_csv("results/elos.csv", index=False)

dtale.show(df_elos)

# %%
