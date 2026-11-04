# Research: integration paths (scout, Nov 3, 2026)

**Report: web research for the signal-timing hackathon pitch (as of 2026-11-03)**

**1. NTCIP 1202 (ASC objects)**
NTCIP 1202 defines the SNMP object definitions for actuated signal controllers (ASCs), meant to be used with NTCIP 1201 (global objects). It covers the central-to-controller interface, not the cabinet hardware. Versions: v01 was approved in 1996, and NEMA NTCIP 1202:2023-10 is listed as current. v04 uses SNMPv3 and does not support SNMPv1. I did not get the standard text, so object-level details (OIDs, phase/pattern table names) are unverified.
- https://local.iteris.com/arc-it/html/standards/standard36.html
- https://ite.org/technical-resources/topics/standards/ntcip-1202-v04-actuated-signal-control-asc
- https://www.dinmedia.de/en/standard/nema-ntcip-1202/374389613
- https://www.its.dot.gov/StandardsTraining/mod31/ppt/m31ppt.pdf

**2. High-resolution logs and ATSPM (our READ path)**
UDOT's ATSPM FAQ says ATSPM "show real-time and a history of performance at signalized intersections." It says the logs use the Indiana Traffic Signal Hi Resolution Data Logger Enumerations, encoded "to the nearest 100 milliseconds," with "over 125 various enumerations," pulled by FTP from the controller. It lists controllers including Econolite, Intelight, Siemens, McCain and TrafficWare. The FAQ does not name a license. The UDOT/FHWA material says the code is open source. I could not confirm the license from the repo. The event code numbers are not verified: two secondary sources disagree, so use the Purdue enumeration document directly.
- https://udottraffic.utah.gov:443/atspm/FAQs/Display
- https://www.nationalacademies.org/read/29326/chapter/4
- https://transportationops.org/news/headline-news/udot-spm-source-code-transition-open-source-fall-mark-taylor

**3. Central systems (ATMS)**
- Cubic's Trafficware ATMS.now (formerly Naztec): a trade source says it is used by 200 cities. Cubic claims more than 300 major ATMS installations and more than 50,000 intersections. These are vendor figures.
- SynchroGreen is the adaptive module. Its brochure says it works with Transit Signal Priority and Emergency Vehicle routing.
- Econolite Centracs: I found no public, documented API for exporting timing data. An Econolite UserVoice request for an open API exists, but that is a proposal. The concrete path is PTV Vistro: Centracs timing programs can be imported into Vistro, and optimized patterns can be sent back to Centracs. The Centracs Interoperability module exists, but I found no specs.
- TACTICS and Kinetic Mobility: not found.
- Cupertino: Cubic's release (dated April 8, 2019) says Trafficware "was selected by the city of Cupertino" for its ATMS, and "The agreement includes services to install as well as integrate existing and new intersection traffic controllers citywide." I found no later rollout updates.
- https://www.cubic.com/news-events/news/cubics-trafficware-upgrades-city-cupertino-central-transportation-management
- https://www.publicworks.com/doc/cubic-s-trafficware-city-cupertino-central-transportation-management-system-0001
- https://www.traffictechnologytoday.com/news/cubics-trafficware-releases-latest-version-of-its-traffic-management-platform.html
- https://go.cubic.com/hubfs/CTS%20Collateral/ITS/Datasheets/ITS-TW-DS-ATMS-2107251.pdf
- https://www.econolite.com/?p=11836 (Vistro/Centracs integration; content seen in search summary only)
- https://econolite.uservoice.com/forums/241856-general/suggestions/50298225-enhanced-open-api-for-real-time-and-historical-tra

**4. Google Project Green Light**
Post dated October 10, 2023 (Yossi Matias). Google's AI and Maps driving trends model each intersection and recommend changes to existing signal plans. Recommendations go to city engineers through the Green Light interface. Cities implement changes "in as little as five minutes" and see results "within weeks." The post says the work "works with existing infrastructure and traffic systems" and does not mention new hardware. The post says the early numbers "indicate a potential for up to 30% reduction in stops and up to 10% reduction in emissions." Footnotes say the stop figure comes from early data and the emissions figure from a DOE model with a single-vehicle-type approximation. The 12 cities named: Abu Dhabi, Bali, Bangalore, Budapest, Haifa, Hamburg, Hyderabad, Jakarta, Kolkata, Manchester, Rio de Janeiro, Seattle. Boston is a US deployment per a boston.gov page I saw in search results but did not open.
- https://blog.google/outreach-initiatives/sustainability/google-ai-reduce-greenhouse-emissions-project-greenlight/
- https://www.boston.gov/node/16372851

**5. Safety and cybersecurity**
- Conflict monitor: a separate hardware device that watches outputs for conflicting greens and forces flash or another safe state. The controller picks phases; the monitor overrides it. In NEMA TS 2 designs it is called the MMU. Conflicting phases are set by a physical card, not software. These claims come from study-guide sites, not the NEMA text.
- CISA ICSA-23-026-02 (Econolite EOS, "Update A"): affected versions "prior to 3.2.23." CVE-2023-0452 (weak hash, CVSS 9.8) and CVE-2023-0451 (improper access control, 7.5). Original publication January 26, 2023; last revised June 22, 2023. Recommendations: update, isolate control networks behind firewalls, keep devices off the internet, use VPNs for remote access.
- NTCIP security: the working group moved v04 to SNMPv3 after the NTCIP 9014 security assessment. Indiana's architecture recommends TLS for center-to-field SNMPv3.
- Siemens and Cubic advisories: not found.
- https://cisa.gov/uscert/ics/advisories/icsa-23-026-02
- https://ite.org/technical-resources/standards/infrastructure-standard-security-implementation-issi
- https://its.indympo.gov/html/comm/solution122.html
- https://www.ite.org/ITEORG/assets/File/NTCIP%20Protocol%20TF%20White%20Paper.pdf

**6. Realistic 3-step path**
1. Read-only: counts, ATSPM/high-resolution logs (UDOT's software and Purdue enumerations are public), timing sheets via a public-records request (not searched).
2. Recommendation card reviewed and entered by an engineer. Green Light is the closest model: recommendations delivered to engineers, who apply them in their own systems.
3. Central-system integration via NTCIP, only with approval. Econolite's Vistro import/export is a vendor-supported path to check first.

Pilots: Pittsburgh's Surtrac 2.0 gave city staff a web interface to adjust timing parameters, which shows city-side control over vendor plans. The approval workflow is not described. https://www.cmu.edu/metro21/projects/safe-mobility/surtrac_2.0.html

**Facts we can say about Cupertino (sourced)**
- Cupertino selected Trafficware (Cubic) for its ATMS central system, announced April 8, 2019; scope includes installing and integrating existing and new controllers citywide. (Sources in section 3.)
- Stevens Creek Blvd and De Anza Blvd Traffic Signal Synchronization Project, RFP PW-2026-853: posted 9/1/2026, closing 09/30/26 at 5:00 PM, status "Under Evaluation" on the city's bid page when I checked. No award notice found.
- https://apps.cupertino.org/bidManagement/index.aspx

**Not found:** Cupertino's signal count, any ITS master plan, any adaptive pilot, and any Cupertino controller model or firmware.

**Things to NOT claim**
- That Cupertino's signals are on a particular Centracs or ATMS version, or that they export data.
- The Stevens Creek project's scope, budget, or award.
- The Green Light 30%/10% as typical results. They are "up to" early figures.
- Specific Indiana event codes.
- Any Econolite API.
- Siemens or Cubic vulnerabilities.
- That the UDOT ATSPM license is confirmed.
- That any agency has an approval workflow for third-party timing cards.

Not checked: the NTCIP standard text, the Purdue enumeration document, the Cupertino master plan and council minutes, and public-records practice. The NTCIP FDOT and Indiana sources came from search snippets, not full pages.


# Research: hardware basics (scout, Nov 3, 2026)

**Traffic-signal hardware and timing: sourced report**

Caveat: I did not open the 2nd edition text. Its NCHRP Report 812 catalog page is https://www.nap.edu/catalog/22097, but the NAP chapters did not load. Definitions below come from the archived 1st edition (ch. 6), which says it "is an archived publication and replaced with the Signal Timing Manual - Second Edition." Many claims are search snippets I did not open; I flag those.

**1. The signal cabinet.** A cabinet holds the controller, a conflict monitor (or MMU), load switches that turn each signal head on and off, detector interface cards, a power supply and a flasher. Communications gear (modem or Ethernet module) connects it to the central system. Caltrans-spec cabinets list a Model 210 conflict monitor, flash transfer relays and railroad relays. The Econolite 332LS datasheet is a snippet only: https://www.econolite.com/wp-content/uploads/2025/02/332LS-Caltrans-TEES_datasheet-2025_digital.pdf. An Ontario plan lists a 2070 controller, conflict monitor, loop detector, load switch, DC isolator and UPS: https://tcp.mto.gov.on.ca/sites/default/files/2024-01/SSP%20622F03_TCP.pdf (snippet). The Iowa DOT cabinet spec returned 404, so I could not verify it.

**2. Controller types and what the computer does.** NEMA TS 2 is a NEMA standard; the current version is TS 2-2021 (https://webstore.ansi.org/preview-pages/NEMA/preview_NEMA+TS+2-2016.pdf for the older 2016 preview; 2021 status per https://infostore.saiglobal.com/en-au/standards/nema-ts-2-2021-781817_saig_nema_nema_3079873/). ATC is the newer Advanced Transportation Controller standard. The 2070 is Caltrans' platform (Econolite's 2070LX+ was redesigned to meet Caltrans TEES 2020). Brands from snippets: Econolite Cobalt (Linux ATC, https://www.econolite.com/wp-content/uploads/2024/03/Cobalt-Rackmount_datasheet-2024_digital.pdf) and ATC 2070LX (https://www.econolite.com/wp-content/uploads/2024/03/ATC_2070LX_datasheet-2024-digital.pdf); Cubic Trafficware ATC Commander and 2070 (https://cubic.com/sites/default/files/2023-03/TW-980-Controller-Data-Sheet_0.pdf); Yunex, formerly Siemens, M60/2070LX (https://www.westernsystems-inc.com/product/yunex-traffic-2070lx-atc/); McCain, a SWARCO company, 2070EN2 (https://www.mccain-inc.com/products/controllers/2070-controllers/2070en1-nema-controller). "Kinetic" was not found. The computer runs the timing: it steps through phases using the stored plan, detector calls and the clock. Hennepin County's concept document says "the ATC controls the functions of a traffic signal" (https://www.hennepin.us/-/media/hennepinus/business/work-with-hennepin-county/transportation-signals/concept-ops-systems.pdf).

**3. Detection and actuation.** Inductive loops are wires cut into the pavement. FHWA says "Five turns of wire are standard... three turns considered to be the minimum acceptable" (https://www.fhwa.dot.gov/publications/research/operations/ITS/06139/chapt5c.cfm). FHWA-cited research says loop failures are often in the wire or splice. The sensing principle (inductance change) is from a vendor source and not verified in FHWA text. Video: Econolite Autoscope Vision (https://www.econolite.com/wp-content/uploads/2024/10/AutoscopeVision_datasheet-2024_digital.pdf) and Iteris Vantage (https://iteris.com/node/16). Radar: Wavetronix SmartSensor Matrix, a stop-bar radar (https://www.intertraffic.com/products-and-services/wavetronix/products/smartsensor-matrix). Dubuque's engineer cited about $5,000 per device, four per intersection (https://www.telegraphherald.com/news/tri-state/article_35e9be5d-d3db-5aa0-9d1e-ca83483bdfd4.html). Actuated terms: gap-out is when the gap timer expires before the max timer; max-out is when the max timer ends the green (https://www.webpages.uidaho.edu/TrafficSignalSystems/traffic/instructor/A17.pdf). Recall gives right-of-way to a phase with no detected demand (https://portal.ct.gov/-/media/DOT/documents/dpublications/VehicleDetectionpdf.pdf).

**4. Conflict monitor / MMU.** It watches for conflicting greens and unsafe voltages, and on a fault it drops power to the flash transfer relays so the intersection goes to flash. Texas DOT says "malfunction flash mode is used when the conflict monitor senses a malfunction" (https://www.txdot.gov/manuals/trf/tff/operational_considerations/flashing_operation-i999358/malfunction_flash-i999378.html). A study guide puts the trip at about 200 to 450 ms, which is not a primary source (https://open-exam-prep.com/study-guides/imsa-traffic-signal-i/cabinet-wiring-and-components/cmu-and-mmu). Manufacturer thresholds are in the Reno MMU-1600G manual (https://manuals.online/reno/server/mmu-1600g-series/user-manual/20ept). The TS1 CMU vs TS2 MMU naming came from a snippet with no confirmed source.

**5. How timing is organized.** FHWA (archived ch. 6): "Cycle length defines the time required for a complete sequence of indications"; "splits are the portion of time allocated to each phase"; offset is "the time relationship between coordinated phases defined reference point and a defined master reference" (https://ops.fhwa.dot.gov/publications/fhwahop08024/chapter6.htm). Time-of-day: "The time-of-day schedule determines what time a plan will be active" (same page). Ring and barrier: "Ring 1 consists of a sequence of phases and Ring 2 consists of the concurrent phases"; "the barrier separates intersecting movements" (same page). An eight-phase dual-ring diagram is in the Tennessee DOT manual (https://www.tn.gov/content/dam/tn/tdot/traffic-engineering/tdmanualrewrite/CHAPTER%204%20-%20TRAFFIC%20SIGNAL%20DESIGN%20-%20OPERATIONS%20AND%20COORDINATION.pdf, snippet only).

**6. How a change reaches the light.** Timing is stored per plan in the controller. It is changed at the cabinet (laptop or front panel) or remotely through a central ATMS. Hennepin says its ATMS lets staff "monitor and control all traffic elements, including remote management of ATCs," but its timing still goes by manual import into Synchro (same Hennepin PDF). Communications: Oregon names fiber as preferred, then 4.9 GHz radio, cellular and leased Ethernet (https://www.oregon.gov/odot/Engineering/Documents_TrafficStandards/Signal-Design-2024-07.pdf, snippet). Dallas says cellular is "the most viable option" for signals (https://dallas.gov/government/Council%20Meeting%20Documents/ttrp_3_advanced-traffic-management-system-project-update_combined_022717.pdf). Michigan connected 286 intersections to Econolite Centracs (https://www.econolite.com/in-action/case-study/michigan-central-signal-control-system). Authority: city codes usually give the city traffic engineer signal-timing authority, e.g. https://ecode360.com/43392255 and https://monterey.municipal.codes/Code/20-33. Whether technicians may change timing was not found.

**7. Cost.** Controller and cabinet: an old FHWA ITS cost entry lists about $15,100 (2005 dollars) for a controller and cabinet with installation (https://www.itskrs.its.dot.gov/its/benecost.nsf/ID/9a313f7d2270043185256f1f00618f19). Florida DOT lists a controller assembly at $9,000 each (https://wbt.dot.state.fl.us/ois/TSMO/TrafficSignalBudgetingCostsAccessibleTables.htm, unit unclear). Adaptive control: 2013 survey about $28,725 average per intersection (https://www.itskrs.its.dot.gov/2013-sc00278, attribution unconfirmed). A Florida 2021 study: $30,000 to $96,400 (source unconfirmed). Colorado 2012: $20,300 to $82,300 (source unconfirmed). Most figures are 2005 to 2015 and unverified. Current pricing was not found.

**Common misconceptions to avoid in a pitch**
1. Loops are not the only detection. Video and radar are common now.
2. "Actuated" does not mean the light reacts instantly. Min and max greens bound every phase.
3. Adaptive control does not replace the cabinet or controller. It sits on top of them.
4. The conflict monitor is a separate safety device, not part of the controller.
5. Cost numbers above are old and unverified. Do not quote them as current.

**Not found or not verified:** the 2nd-edition chapters on hardware and timing storage; current cabinet and adaptive pricing; technician authority; "Kinetic" as a brand; the NEMA TS1 vs TS2 difference with a confirmed source.

# Rule for the console
Use only claims marked sourced above. Skip anything flagged snippet-only, unverified, or not found. No cost numbers. No vendor names for Cupertino beyond "Cupertino chose Cubic Trafficware for its central system (2019 announcement)".
