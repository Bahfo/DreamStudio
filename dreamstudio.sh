#!/bin/bash

# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# ---------------------------------------------------------------------
# The DreamStudio entrance point - Serves as the main shell entrance to 
# run DreamStudio from a shell. This is for development mode and 
# developers only. 

set -e 

readonly YELLOW='\033[0;33m'
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

clear 2>/dev/null || true

function show_guide() {
clear 2>/dev/null || true
printf "
${GREEN}================================================================================${NC}
                   ${YELLOW}DEVELOPER AGREEMENT AND CODE OF CONDUCT${NC}
${GREEN}================================================================================${NC}

By accessing, contributing to, or utilizing the DreamStudio IDE in
development mode, you expressly acknowledge, understand, and agree to the
following terms, conditions, and policies set forth by EXcellent TechStacks:

  ${GREEN}[1]${NC} GPLv3 License & Source Code
      The source code for DreamStudio is licensed under the GNU General
      Public License v3.0 (GPLv3). The full license text is available in 
      the ${YELLOW}LICENSE.md${NC} file located in the root directory.

  ${GREEN}[2]${NC} Contributor Assignment & IP Terms
      All code submissions, patches, and contributions provided by you 
      are subject to EXcellent TechStacks' Contributor Terms of Service. 
      By participating, you assign your contributions in accordance with 
      company policy. All contributors must maintain a professional and 
      respectful demeanor. Harassment, threats, violence, or discriminatory 
      language (including sexism, racism, homophobia, transphobia, and 
      ableism) of any kind is strictly prohibited.

  ${GREEN}[3]${NC} Harassment and Conduct Standards
      Unacceptable conduct includes, but is not limited to, unwanted 
      sexual attention, advances, comments, or jokes, as well as personal 
      insults or attacks based on gender, sexual orientation, race, religion, 
      disability, or socioeconomic status.

  ${GREEN}[4]${NC} Professionalism and Empathy
      All participants are expected to exercise professional courtesy, 
      respect, and empathy. Differences in technical expertise and 
      learning stages must be approached with patience and constructiveness.

  ${GREEN}[5]${NC} Enforcement and Legal Remedies
      EXcellent TechStacks reserves all legal rights and remedies to 
      pursue appropriate legal action against any individual who breaches 
      these terms or engages in malicious, unlawful, or harmful conduct.

${GREEN}--------------------------------------------------------------------------------${NC}
${YELLOW}REPORTING VIOLATIONS:${NC}
If you experience or witness a violation of this Code of Conduct, or if 
you prefer not to address the individual directly, please submit a 
confidential report to EXcellent TechStacks at:
${YELLOW}codeofconduct@extechs.mail${NC}

${YELLOW}CONSEQUENCES OF NON-COMPLIANCE:${NC}
Violations of these policies will not be tolerated. Immediate compliance 
with remediation requests is mandatory. EXcellent TechStacks reserves 
the right to take any disciplinary or legal action deemed necessary, 
up to and including permanent revocation of access, termination of 
contribution privileges, and further legal proceedings.
${GREEN}================================================================================${NC}



Please press ${YELLOW}[A]${NC} if you agree, otherwise, press ${YELLOW}[D]${NC} to quit.
"

read -n 1 -s key
echo

if [[ "$key" == "A" || "$key" == "a" ]]; then
    user_accepted
else
    echo "Exiting ..."
fi
}

function mainloop() {
printf "${YELLOW}
Welcome to DreamStudio Integrated Development Environment!${NC}

This project is maintained and developed by EXcellent TechStacks.
"

printf "${GREEN}"
cat <<'LOGO'
            _______    _______       __         
            | ____\ \/ /_   _|__  ___| |__  ___ 
            |  _|  \  /  | |/ _ \/ __| '_ \/ __|
            | |___ /  \  | |  __/ (__| | | \__ \
            |_____/_/\_\ |_|\___|\___|_| |_|___/
        (C) COPYRIGHT 2026 EXcellent TechStacks


LOGO
printf "${NC}"

printf "${YELLOW}IMPORTANT:${NC} 
You are in development mode of DreamStudio. This mode allows you to
access experimental features and several still-in-development codes.

${RED}Please read in caution the following as it contains important info
and warnings. Continue only if you agree.${NC}

Press ${YELLOW}[E]${NC} to read the guide (no acceptance required here).
"

read -n 1 -s key
echo

if [[ "$key" == "E" || "$key" == "e" ]]; then
    show_guide
else
    echo "Incorrect key pressed. Action canceled."
fi
}

function user_accepted() {
clear 2>/dev/null || true
printf "Thank you for accepting the code of conduct.
Preparing Developer's Tools and Extraction ...\n
"
sleep 5
}

function startup() {

}

function mainsdevscreen() {
clear 2>/dev/null || true

printf "${YELLOW}"
cat <<'LOGO'
 ____                           ____  _             _ _       
|  _ \ _ __ ___  __ _ _ __ ___ / ___|| |_ _   _  __| (_) ___  
| | | | '__/ _ \/ _` | '_ ` _ \\___ \| __| | | |/ _` | |/ _ \ 
| |_| | | |  __/ (_| | | | | | |___) | |_| |_| | (_| | | (_) |
|____/|_|  \___|\__,_|_| |_| |_|____/ \__|\__,_|\__,_|_|\___/ 

LOGO
printf "${NC}"

echo "DreamStudio | EXcellent TechStack"
echo "Copyright (C) 2026 - All Rights Reserved."
echo "Visit us at: https://homepage.xtechstax.duckdns.org/"
printf "%b\n" "${RED}DreamStudio is licensed under the GPLv3 License.${NC}"
printf "\n"
}

mainloop