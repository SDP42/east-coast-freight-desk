import { clsx, type ClassValue } from "clsx";

/** Class-name helper used by the React Bits / shadcn-style components. */
export const cn = (...inputs: ClassValue[]) => clsx(inputs);
