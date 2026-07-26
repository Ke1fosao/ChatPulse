import type { ResourceState } from "./types";

export function idleResource<T>(data: T | null = null): ResourceState<T> {
  return { status: "idle", data, error: "" };
}

export function loadingResource<T>(current: ResourceState<T>): ResourceState<T> {
  return { status: "loading", data: current.data, error: "" };
}

export function successResource<T>(data: T): ResourceState<T> {
  return { status: "success", data, error: "" };
}

export function errorResource<T>(current: ResourceState<T>, error: string): ResourceState<T> {
  return { status: "error", data: current.data, error };
}
