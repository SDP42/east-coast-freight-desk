export interface HaldiaPhase {
  index: number;
  title: string;
  text: string;
}

export const HALDIA_PHASES: HaldiaPhase[] = [
  { index: 0, title: "Anchorage & lightering", text: "Fully laden vessels wait at Sandheads or Sagar. Floating cranes lighten them so the draft fits the Hooghly channel." },
  { index: 1, title: "River transit", text: "About 130 km and roughly six hours from Sandheads to the jetty, timed to the tide." },
  { index: 2, title: "Lock entry", text: "Haldia is an impounded dock. The vessel enters a 330 m by 39 m lock; the gates close and the level is matched to the dock." },
  { index: 3, title: "Berth 4A discharge", text: "Two grab unloaders work at up to about 14,000 tonnes a day, and the coal goes to the stockyard." },
  { index: 4, title: "Rail to the plants", text: "Wagons carry the coking coal to the steel plants while the vessel clears the berth for the next tide." },
];
