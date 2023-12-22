# %%
from elo import Elo, Rating
import pandas as pd
from tqdm import tqdm
import dtale


# %%
df_fights = pd.read_csv("data/fights.csv", sep=";").sort_values("eventDate")

# df_fights = df_fights[df_fights["weightClass"] == "Heavyweight"]

# %%
def compute_elo(df_fights, elo_env, belt_weight=None):
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

    df_roster["elo"] = 1500

    K_FACTOR = elo_env.k_factor
    for _, row in df_fights.iterrows():
        winner = row["winnerHref"]
        winner_elo = df_roster.loc[df_roster["href"] == winner, "elo"].values[0]

        loser = row["loserHref"]
        loser_elo = df_roster.loc[df_roster["href"] == loser, "elo"].values[0]
        
        if belt_weight:
            elo_env.k_factor = K_FACTOR
            winner_new_elo, loser_new_elo = elo_env.rate_1vs1(winner_elo, loser_elo)

            if row["belt"] == 1:
                elo_env.k_factor *= belt_weight

                elos = elo_env.rate_1vs1(winner_elo, loser_elo, drawn= row["result"] == "draw")

                winner_new_elo = elos[0]

                if row["result"] == "draw":
                    loser_new_elo = elos[1]

        df_roster.loc[df_roster["href"] == winner, "elo"], df_roster.loc[df_roster["href"] == loser, "elo"] = winner_new_elo, loser_new_elo

    return df_roster


# %%
configs = [
    {
        "name": "k64_beta100_belt2",
        "k_factor": 64,
        "beta": 100,
        "belt_weight": 2,
    },
    {
        "name": "k64_beta100_belt3",
        "k_factor": 64,
        "beta": 100,
        "belt_weight": 3,
    },
    {
        "name": "k32_beta100_belt2",
        "k_factor": 32,
        "beta": 100,
        "belt_weight": 2,
    },
    {
        "name": "k32_beta100_belt3",
        "k_factor": 32,
        "beta": 100,
        "belt_weight": 3,
    }
]

dfs = [
    compute_elo(
        df_fights,
        Elo(k_factor=config["k_factor"], beta=config["beta"], initial=1500), 
        belt_weight=config["belt_weight"] if "belt_weight" in config else None
        ).rename(
        columns={"elo": "elo_" + config["name"]}
    )
    for config in tqdm(configs, desc="Computing elo", unit="config")
]

df_elos = dfs[0]
for df in dfs[1:]:
    df_elos = df_elos.merge(df, on=["href", "firstName", "lastName"], how="outer")


# %%
df_elos["lastFightDate"] = None

for i, row in tqdm(
    df_elos.iterrows(),
    desc="Adding last fight date",
    unit="fighter",
    total=len(df_elos),
):
    fighter = row["href"]

    # get the last fighter's fight date
    last_fight_date = df_fights[
        (df_fights["winnerHref"] == fighter) | (df_fights["loserHref"] == fighter)
    ]["eventDate"].max()

    df_elos.loc[i, "lastFightDate"] = last_fight_date

dtale.show(df_elos)

# %%
df_elos_final = df_elos[df_elos["lastFightDate"] > "1022-01-01"]

# a ranking is computed for each elo
for config in configs:
    df_elos_final["rank_" + config["name"]] = df_elos_final["elo_" + config["name"]].rank(
        ascending=False
    )

# dtale.show(df_elos_final)

# %%
top_15_irl = [
    "275aca31f61ba28c",
    "07f72a2a7591b409",
    "e1248941344b3288",
    "f1fac969a1d70b08",
    "e5549c82bfb5582d",
    "07225ba28ae309b6",
    "b50a426a33da0012",
    "0d8011111be000b2",
    "1338e2c7480bdf9e",
    "a0f0004aadf10b71",
    "cb696ebfb6598724",
    "399afbabc02376b5",
    "150ff4cc642270b9",
    "f1b2aa7853d1ed6e",
    "009341ed974bad72",
    "9e8f6c728eb01124"
]

df_elos_final["ranking_irl"] = df_elos_final["href"].apply(lambda x: top_15_irl.index(x) +1 if x in top_15_irl else None)

df_elos_final.sort_values("rank_k32_beta100_belt3").head(26)[
    [
        "firstName",
        "lastName",
        "ranking_irl",
        *["rank_" + config["name"] for config in configs],
    ]
]

 # %%
# calculer l'écarts entre les classements et le classement irl
df_diff = df_elos_final.dropna(subset=["ranking_irl"])
for config in configs:
    df_diff["diff_" + config["name"]] = df_diff["ranking_irl"] - df_diff["rank_" + config["name"]]
    print(config["name"], df_diff["diff_" + config["name"]].mean())

# %%
