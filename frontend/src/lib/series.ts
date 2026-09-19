// The freight series is the USDA monthly grain ocean rate (US government, public domain): a dry-bulk proxy, not a coal rate.
export const PRIMARY = "OCEAN_GULF_JAPAN";
export const FREIGHT_SERIES = [
  { key: "OCEAN_GULF_JAPAN", label: "Grain ocean rate, US Gulf to Japan" },
  { key: "OCEAN_PNW_JAPAN", label: "Grain ocean rate, US Pacific NW to Japan" },
];
export const MONITOR_SERIES = [{ key: "BRENT", label: "Brent crude (daily)" }, { key: "INR", label: "INR per USD (daily)" }, { key: "DXY", label: "US dollar index (daily)" }];
export const DATA_POLICY = "Only public-domain data (US government and Federal Reserve series, NOAA), fetched free with no accounts or keys.";
