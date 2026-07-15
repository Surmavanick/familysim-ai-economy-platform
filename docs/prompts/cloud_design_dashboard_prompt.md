# DemandMind Cloud Design Dashboard Prompt

This file contains a strengthened, production-grade prompt for generating the ideal dashboard for this project in a cloud design tool.

Project context distilled from the codebase:
- Public product brand: `DemandMind`
- Core promise: AI demand forecasting for retail using synthetic Georgian family simulations
- Operating context: Tbilisi districts, household behavior, retail pricing, store intelligence, simulations, auditability
- Product reality: not a generic admin panel, but an intelligence and decision-support system for retail operators, analysts, executives, and category managers
- Existing UX signals in the repo: map-first control room, simulation replay, household stress/budget monitoring, retail chain pricing comparison, event feed, scenario planning, exports, and explainability

## Master Prompt

```text
Design a world-class, enterprise-grade SaaS dashboard for “DemandMind”, an AI retail demand forecasting platform powered by synthetic Georgian household simulations.

This is the internal product dashboard behind the public-facing DemandMind site. It must visually and strategically connect to the existing brand language of the live marketing site while expanding into a serious operational product.

Product truth:
DemandMind is not a generic BI tool and not a simple forecasting table. It is a simulation-native retail intelligence operating system that combines:
- AI demand forecasting
- synthetic family and household simulation
- district-level geospatial analysis inside Tbilisi
- live or recent Georgian retail pricing intelligence
- scenario planning for promotions, inflation, holidays, and shocks
- explainable demand drivers
- audit trail for every important forecast shift

Design objective:
Create a premium “DemandMind Control Center” dashboard that makes a retail executive, buyer, merchandiser, or category manager feel:
“I can see what will sell, why it will sell, where it will sell, which household segments drive it, how confident the forecast is, and what action I should take next.”

The dashboard must feel:
- premium
- credible
- intelligent
- strategic
- map-aware
- simulation-aware
- retail-native
- investor-ready
- operationally useful

Do not design:
- a generic CRM dashboard
- a generic finance dashboard
- a basic admin panel
- a playful consumer app
- a crypto-looking neon interface
- a noisy or rainbow-heavy analytics board

Brand and visual language:
Match the visual DNA of the DemandMind public website:
- dark, premium, cinematic foundation
- restrained cobalt blue accent
- refined typography similar to Geist / modern grotesk
- large confident headings
- spacious but purposeful layout
- crisp white or off-white surfaces where tables and data need clarity
- modern enterprise polish similar to a blend of Stripe, Vercel, Linear, and a high-end retail intelligence control room

Preferred color direction:
- primary dark: #0A0A0F
- panel dark: #111827
- deeper slate: #0F172A
- brand blue: #3B6EF5
- text strong on dark: #F9FAFB
- text secondary: #9CA3AF
- border light on dark: rgba(255,255,255,0.08)
- border on light: #E5E7EB
- surface light: #FFFFFF or #F9FAFB
- positive: emerald green
- caution: amber
- critical: red

Typography:
- strong geometric/grotesk SaaS typography
- excellent hierarchy
- large section titles
- compact uppercase overlines for data zones
- monospaced timestamps or confidence codes where useful

Platform users:
- retail executives
- category managers
- demand planners
- buyers
- pricing analysts
- simulation operators

Primary jobs the dashboard must support:
1. See demand shifts quickly
2. Understand why demand changed
3. Identify which districts and household segments drive change
4. Compare product opportunities and risks
5. Run scenarios
6. Decide inventory and promotion actions
7. Review confidence and data quality
8. Inspect simulation logic and audit trail

Canvas:
Design a desktop-first control center at 1440px to 1600px wide.
Use a sophisticated 12-column grid.
Make the main experience dark mode first.
Allow selective lighter embedded surfaces for data-heavy tables, sheets, or comparison modules.
Create a polished, realistic product mockup rather than a loose concept board.

Main page:
Create the main “Overview / Control Center” dashboard screen.

Top global app shell:
Design a premium top navigation bar and left navigation rail.

Top nav must include:
- DemandMind logo
- workspace or organization switcher
- environment badge: Live / Sandbox / Replay
- global search field: search SKU, product, district, chain, family segment
- date range picker
- latest simulation run timestamp
- notifications icon
- help or docs icon
- user avatar
- primary button: Run Simulation
- secondary button: New Scenario

Left sidebar navigation:
- Overview
- Forecasts
- Simulations
- Family Segments
- District Map
- Retail Intelligence
- Scenarios
- Alerts
- Audit Trail
- Reports
- Settings

Sidebar should feel premium, slim, and clean:
- icon + label
- current page highlighted
- elegant hover states
- persistent but unobtrusive

Hero area at top of page:
Include:
- page title: DemandMind Control Center
- subheading: Live retail demand intelligence powered by Georgian family simulations
- a small status strip showing:
  - environment
  - simulation status
  - data freshness
  - forecast version
- buttons:
  - Run Simulation
  - Compare Scenarios
  - Export Forecast Pack
  - Share Report

Top KPI row:
Design 6 premium KPI cards with micro-motion, subtle glow on hover, and clear deltas.

The 6 KPI cards:
1. Forecast Accuracy
2. Products Monitored
3. High-Demand Items
4. Avg Confidence Score
5. Active Family Agents
6. Revenue Opportunity or Stockout Risk

For each KPI card include:
- label
- main metric
- delta vs previous simulation run
- miniature sparkline or trend microchart
- tiny caption
- semantic state color
- info tooltip

Examples of strong KPI copy:
- Forecast Accuracy: 94.1%  +1.8%
- Products Monitored: 12,480
- High-Demand Items: 214  +38 this week
- Avg Confidence: 88.6%
- Active Agents: 10,240 households
- Revenue Opportunity: ₾1.24M

Primary content architecture:
Create a 3-zone dashboard:

Zone 1:
Large central intelligence module taking the most visual weight.

Zone 2:
Right-side intelligence rail with alerts, recommendations, simulation health, and change summaries.

Zone 3:
Lower analytical grid with deeper charts, explainability, pricing intelligence, family segment analysis, and scenario tools.

Zone 1: Central intelligence module
This must be the visual heart of the product.
Design it as a large premium card with segmented tabs:
- Demand Map
- Forecast Grid
- Simulation Replay

Mode A: Demand Map
Create a large interactive Tbilisi intelligence map.

Map purpose:
- show where demand pressure is forming
- show which districts are driving product demand
- show live or replayed household movement and pressure
- show store network and chain distribution
- show stress, budget, and demand hotspots

Map should contain:
- district overlays for Tbilisi
- clearly labeled districts:
  - Vake
  - Saburtalo
  - Old Town / Metekhi
  - Nadzaladevi
  - Stadion
  - Gldani
  - Varketili
  - New Batumi
- store location markers
- demand hotspot glow layers
- stress heatmap overlay
- optional household movement traces
- current selected district highlight
- map legend
- layer controls
- zoom controls
- full-screen toggle
- timeline replay strip

Top controls for map:
- district filter
- retail chain filter
- category filter
- household type filter
- confidence threshold filter
- stress threshold filter
- layer toggles
- replay slider
- play/pause
- speed toggle 1x / 2x / 5x / 10x

Suggested layer options:
- Demand Heat
- Household Stress
- Budget Pressure
- Shopping Routes
- Store Chains
- District Labels
- Promotion Impact

Selected district inspector:
When a district is clicked, open a premium side panel within the module.
This inspector must show:
- district name
- district tier or economic profile
- average salary
- unemployment
- household count
- average demand uplift
- dominant household profile
- top 3 fast-rising product categories
- top chains visited
- stockout risk indicator
- stress trend mini chart
- promotion sensitivity
- buttons:
  - View District Report
  - Run Local Scenario
  - Compare Districts

Mode B: Forecast Grid
Create a sophisticated table view for product-level forecasting.

This is a decision table, not a plain spreadsheet.
It should look highly polished and enterprise-grade.

Columns to include:
- Product
- SKU
- Category
- Store Chain
- Baseline Demand
- Forecast Demand
- Trend
- Confidence
- Top Driver Segment
- District Driver
- Recommended Order Qty
- Margin Impact
- Stockout Risk
- Promo Sensitivity
- Actions

Each row should visually support:
- trend arrow or pill
- confidence bar
- hover insight preview
- quick compare checkbox
- favorite or pin
- action menu

Top controls above table:
- Search products
- Filter
- Sort
- Saved Views
- Export CSV
- Export PDF
- Open Comparison
- Create Scenario From Selection

Make the table visually strong by including:
- frozen first column
- lightweight separators
- row hover detail reveal
- expandable drawer for product reasoning
- clean use of blue and semantic colors

Mode C: Simulation Replay
Create a cinematic operational replay panel.

Purpose:
- show how the simulation evolved
- let the user inspect key moments that changed the forecast
- build trust in the model

Include:
- horizontal replay timeline
- event markers
- play/pause
- step forward/back
- speed control
- time window summary

Example event markers:
- payday
- promotion launch
- competitor price cut
- inflation spike
- holiday effect
- weather shift
- utility bill pressure
- salary bonus
- stockout event

Replay should visualize:
- household movement
- budget pressure over time
- stress evolution
- category demand curves
- district-level change
- confidence stabilization

Right-side replay annotation panel:
- “What happened here?”
- key driver explanation
- impacted products
- impacted family segments
- impacted districts
- resulting recommendation

Zone 2: Right intelligence rail
Design a stacked intelligence sidebar with compact but high-value cards.

Card 1: What Changed
Show the top 5 forecast changes since last run.
Each item should include:
- product or category
- percentage change
- small arrow
- short reason tag
- confidence badge

Reason tags:
- Payday Effect
- Promotion Lift
- District Stress
- Competitor Pricing
- Seasonal Shift
- Family Budget Compression
- Category Substitution

Card 2: Recommended Actions
This is crucial.
Show prioritized decision recommendations.
Each action must have:
- title
- short rationale
- impact score
- urgency
- CTA button

Examples:
- Increase order volume for coffee in commuter districts
- Reduce detergent allocation in low-confidence zones
- Extend dairy promotion in Saburtalo
- Watch stockout risk in Vake convenience formats
- Re-run scenario for beverages after competitor discount

Card 3: Simulation Health
Show operational trust signals:
- simulation status
- active agent count
- last run duration
- data freshness
- retail feed freshness
- anomaly status
- confidence engine health
- forecast version

Card 4: Alerts
Show alerts with severity styling:
- low confidence forecast
- abrupt district demand spike
- missing pricing feed
- unusual household stress increase
- chain-level pricing anomaly
- category substitution warning

Each alert should include:
- severity
- timestamp
- location or product
- investigate button

Card 5: Team Notes or Watchlist
Optional but valuable.
Include:
- pinned products
- pinned districts
- analyst note
- assigned tasks

Zone 3: Lower analytical intelligence grid
Create a modular grid of rich analytical cards.
This section should feel deep, useful, and premium.

Must include the following modules:

1. Family Segment Breakdown
This is a key product differentiator.
Show major synthetic family segments:
- Working Couples
- Single Parents
- Multi-Generational Families
- Students / Young Adults
- Pensioner Households

For each segment show:
- share of demand
- price sensitivity
- average budget pressure
- stress level
- preferred chains
- preferred categories
- promotion responsiveness
- district concentration
- button: View Segment

Visual treatment:
- card-based segment list or ranked panel
- icons or archetype badges
- clean mini charts
- a segment comparison row

2. Retail Intelligence
Create a polished pricing intelligence panel comparing Georgian chains.

Chains to visually reference:
- Spar
- Carrefour
- Nikora
- Goodwill
- Daily
- Magniti
- 2 Nabiji
- Libre
- Agrohub

Show:
- cheapest chain today
- biggest category price mover
- promotion density
- average basket cost
- price spread by category
- freshness timestamp

Controls:
- Compare Chains
- View Price History
- Export Snapshot
- Open Basket Simulation

3. Demand by District
Bar or heat-based chart:
- compare demand intensity by district
- allow quick scan for geographic concentration
- include filter chip for category

4. Category Demand Mix
Show how product categories contribute to forecasted volume:
- grocery
- beverages
- dairy
- bakery
- snacks
- household
- personal care
- pharmacy

5. Confidence Distribution
Show histogram or segmented bar:
- high confidence
- medium confidence
- low confidence
Include a CTA:
- Review Low Confidence Forecasts

6. Stockout Risk vs Overstock Risk
Create a risk quadrant:
- x-axis: overstock exposure
- y-axis: stockout risk
- bubble size: revenue
- color by confidence

7. Seasonal Demand Calendar
Show how seasonal events affect demand:
- New Year
- Easter
- school-year start
- winter heating pressure
- summer tourism
- promotion windows

8. Explainability / Audit Trail
This is a signature product module.
Design a beautiful explanation card answering:
“Why did this forecast move?”

Show:
- primary demand drivers
- confidence contribution weights
- causal chain
- linked events
- related districts
- related family segments
- related pricing changes
- source tags
- “Open Full Reasoning” button

Example explanation language:
- Coffee demand rose due to payday effect, commuter stress, and concurrent chain promotion in central districts.
- Dairy demand softened because low-income households shifted to lower-cost substitutes after utility bill pressure.

Scenario Planning module
This must feel powerful and premium, not like a simple form.

Design a “New Scenario Composer” card or side panel with controls:
- scenario name
- product selection
- category selection
- district targeting
- store chain targeting
- discount percentage
- price increase / decrease
- promotion start date
- duration
- inflation shock
- holiday event
- payday shift
- competitor reaction
- simulation duration

Actions:
- Run Scenario
- Duplicate Scenario
- Compare To Baseline
- Save Scenario
- Share Scenario

Also include a small scenario result preview showing:
- expected lift
- confidence delta
- highest affected districts
- most responsive family segments

Product Deep Dive modal
Design one open modal state.

It should include:
- product image placeholder
- product name
- SKU
- category
- baseline demand
- forecast demand
- confidence score
- historical trend line
- top districts
- top family segments
- preferred chain environments
- pricing sensitivity
- substitution risk
- recommended order range
- explanatory narrative
- actions:
  - Export
  - Compare
  - Run Scenario
  - Assign

District Report drawer
Design one expanded district drawer state with:
- district profile
- demand composition
- chain presence
- household mix
- price sensitivity
- stress/budget pressure trends
- recommended action plan

Alert Investigation panel
Design one alert deep-dive state showing:
- root cause summary
- timeline
- impacted products
- impacted chains
- impacted districts
- recommended mitigation

Microcopy style:
Use calm, confident, executive copy.
Avoid hype.
Prefer phrases like:
- Forecast Confidence
- Demand Drivers
- Simulation Health
- District Pressure Index
- Household Budget Stress
- Chain Price Spread
- Retail Feed Freshness
- Promotional Lift
- Recommended Order Quantity
- Explain Forecast
- Audit Trace
- Compare To Baseline

Interaction behavior:
- elegant hover states
- subtle panel elevation
- refined loading skeletons
- animated KPI counts
- smooth timeline scrubbing
- collapsible inspector panels
- clear semantic alert states
- sticky table controls
- compact premium tooltips

Design language for surfaces:
- rounded but not soft consumer-style
- thin borders
- subtle translucency in top-level overlays if helpful
- careful use of glow only for active intelligence states
- premium spacing and rhythm
- strong contrast and legibility

Required buttons and controls to visibly include:
- Run Simulation
- Pause Simulation
- New Scenario
- Compare Scenarios
- Export PDF
- Export CSV
- Share Report
- View Product
- View District
- View Segment
- Investigate Alert
- Open Audit Trail
- Save View
- Reset Filters
- Full Screen Map
- Add Note
- Assign to Team

Responsive guidance:
Tablet:
- collapse right rail into tabs or slide-over
- keep central map/table area dominant
- convert KPI row into 2-column or 3-column grid

Mobile:
- prioritize KPI cards and top changes
- convert filters to bottom sheet
- convert map to reduced-height panel
- turn complex tables into stacked product cards
- keep Run Simulation and New Scenario visible

Final composition requirement:
The final dashboard should look like the real operating system behind DemandMind’s premium marketing site.
It should visually bridge:
- the cinematic promise of the public brand
- the analytical trust of enterprise forecasting software
- the geospatial richness of a map-based retail simulation
- the depth of an explainable AI system

The final output should include:
- the full desktop overview screen
- a selected district state
- a selected product modal
- a scenario planning state
- one explainability state
- one alert investigation state

Make the result feel like the most compelling retail intelligence dashboard in the Georgian market.
```

## Reinforcement Block

Use this additional block if the design tool benefits from stronger constraints:

```text
Extra instructions:
- Prioritize clarity over decoration
- Make the map module feel central and strategic
- Make forecasting confidence highly legible
- Show strong information hierarchy
- Keep the dashboard visually premium and restrained
- Ensure every major panel answers a real business question
- Avoid empty decorative cards
- Avoid generic analytics filler
- Use realistic Georgian retail language, districts, and supermarket chains
- Make scenario planning and explainability feel like flagship differentiators
- Blend executive overview and operator control in one coherent screen
```

## Compact Copy-Paste Version

Use this if the tool prefers a shorter but still strong prompt:

```text
Design a premium dark-mode enterprise dashboard for DemandMind, an AI retail demand forecasting platform powered by synthetic Georgian family simulations. This is the internal control center behind a polished public brand, so it must feel cinematic, premium, and operationally intelligent, not like a generic admin panel.

The dashboard should combine:
- AI demand forecasting
- Tbilisi district-level geospatial analysis
- household segment simulation
- live retail chain pricing intelligence
- scenario planning
- explainability and audit trail

Use a visual language that matches a high-end SaaS product: dark charcoal foundation, cobalt blue accent, refined modern typography, crisp data surfaces, subtle motion, and strong hierarchy. The main experience should be a “DemandMind Control Center” with top KPIs, a large central intelligence canvas, a right-side intelligence rail, and a lower analytical grid.

Include a premium top nav with logo, environment badge, global search, date range, last simulation timestamp, notifications, Run Simulation, and New Scenario. Include a left sidebar with Overview, Forecasts, Simulations, Family Segments, District Map, Retail Intelligence, Scenarios, Alerts, Audit Trail, Reports, and Settings.

Top KPI cards: Forecast Accuracy, Products Monitored, High-Demand Items, Avg Confidence Score, Active Family Agents, Revenue Opportunity or Stockout Risk.

Central module must have tabs:
1. Demand Map
2. Forecast Grid
3. Simulation Replay

Demand Map should show Tbilisi districts, store markers, demand hotspots, household stress heatmap, movement traces, layer toggles, replay controls, and a district inspector panel with salary, unemployment, household count, top categories, top chains, stress trend, and actions.

Forecast Grid should be a rich enterprise table with product, SKU, category, chain, baseline demand, forecast demand, confidence, top family segment, top district, recommended order quantity, margin impact, stockout risk, and actions.

Simulation Replay should show a timeline with markers for payday, promotion launch, inflation spike, holiday effect, competitor discount, and other key events, plus a side panel explaining what changed.

Right rail must include:
- What Changed
- Recommended Actions
- Simulation Health
- Alerts
- Optional Team Notes / Watchlist

Lower grid must include:
- Family Segment Breakdown
- Retail Intelligence by chain
- Demand by District
- Category Demand Mix
- Confidence Distribution
- Stockout vs Overstock Risk
- Seasonal Demand Calendar
- Explainability / Audit Trail
- Scenario Planning module

Family segments: Working Couples, Single Parents, Multi-Generational Families, Students / Young Adults, Pensioner Households.

Retail chains: Spar, Carrefour, Nikora, Goodwill, Daily, Magniti, 2 Nabiji, Libre, Agrohub.

Tbilisi districts: Vake, Saburtalo, Old Town / Metekhi, Nadzaladevi, Stadion, Gldani, Varketili, New Batumi.

Also design one open Product Deep Dive modal, one District Report drawer, one Alert Investigation state, and one Scenario Planning state.

The final product should make a retail executive instantly understand what will sell, why it will sell, where it will sell, how confident the system is, and what action to take next.
```

