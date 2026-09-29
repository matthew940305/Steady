# Steady first aid site

An English-language, responsive first aid website with short step-by-step guides, a breathing decision path for someone who has collapsed, and timers for CPR rhythm, seizures, and burns. It uses only Python's standard library and has no build step.

## Run locally

For a shared site where edits appear for everyone, run from this folder:

```powershell
python server.py
```

Open `http://localhost:4173/`. Set up the administrator password from the server computer before letting other people access the site. The server stores published content in `content.json` and the salted password verifier in `admin.json`. Keep both files private and back them up. The server binds to `127.0.0.1` by default; `STEADY_HOST` and `STEADY_PORT` can change that. A hosting platform's `PORT` value takes precedence over `STEADY_PORT`.

For public hosting, follow [DEPLOYMENT.md](DEPLOYMENT.md). `STEADY_HTTPS=1` marks login cookies as HTTPS-only; the hosting platform must provide HTTPS separately. `STEADY_DATA_DIR` sets the persistent data directory, and `STEADY_ADMIN_PASSWORD` can provision the first administrator on startup.

For a single-browser static preview, run `python -m http.server 4173` instead, or open `index.html`. In that mode, edits stay in that browser's local storage and do not publish to other devices.

## Edit content

1. Click **Edit content** and create a password of at least eight characters.
2. In **Guides**, edit a guide or add one. Each step can have text, an icon or uploaded image, a note, and an optional timer. A final decision can link to another guide by its ID.
3. Use **Site settings** for the site name, homepage copy, emergency number, and call instructions.
4. Use **Backup & restore** to export or import a JSON backup. The backup excludes the password.

When running `server.py`, edits are saved on the server and visible to every visitor. Only an authenticated administrator can change them. The static preview keeps edits in the browser and its editor password is only a local lock. For a larger public service, add multiple administrator accounts, content approval, monitoring, and professional medical review.

The default emergency number is **119 for Taiwan**. Change it in Site settings before use elsewhere. The call buttons open the device dialer; they do not place a call automatically.

## Guidance sources

Each guide links to its source in the guide view. The sample content is based on:

- [American Red Cross: adult CPR](https://www.redcross.org/take-a-class/cpr/performing-cpr/cpr-steps), [unresponsive and breathing](https://www.redcross.org/take-a-class/resources/learn-first-aid/unresponsive-and-breathing-person), [choking](https://www.redcross.org/take-a-class/resources/learn-first-aid/adult-child-choking), [severe bleeding](https://www.redcross.org/take-a-class/resources/learn-first-aid/bleeding-life-threatening-external), and [burns](https://www.redcross.org/take-a-class/resources/learn-first-aid/burns).
- [American Heart Association: heart attack and stroke warning signs](https://www.heart.org/en/about-us/heart-attack-and-stroke-symptoms) and [CPR](https://cpr.heart.org/en/resources/what-is-cpr).
- [CDC: seizure first aid](https://www.cdc.gov/epilepsy/first-aid-for-seizures/index.html).
- [Taiwan National Fire Agency: 119 and 112](https://www.nfa.gov.tw/cht/index.php?code=list&ids=66).

This site supports immediate first actions. Emergency dispatch instructions and hands-on training take priority. Have a qualified local clinician or first aid instructor review any new or edited medical content before public use.
