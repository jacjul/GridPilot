import { useEffect, useMemo, useState } from "react"
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { APIError, getAPI, patchAPI, postAPI } from "../fetchAPI"

type OptimizationResponse = {
  status: string
  objective: number
  horizon_days?: number
  bess_terminal_soc_policy?: string
  timestamps: string[]
  prices: number[]
  kwh_pv: number[]
  kwh_demand: number[]
  kwh_grid_entnahme: number[]
  kwh_grid_einspeisung: number[]
  kwh_bess_charge: number[]
  kwh_bess_discharge: number[]
  kwh_bess_soc: number[]
  ev: Array<{ ev_id: number; available: boolean[]; kwh_charge: number[]; kwh_soc: number[] }>
  day_advice?: {
    summary: string
    items: string[]
    metrics: Record<string, number>
  }
}

type Me = {
  id: number
  name: string
  lastname: string
  username: string
  email: string
  annual_consumption_kwh: number
  load_profile_type: "SLP" | "SLP_HEATPUMP"
}

type PV = {
  id: number
  latitude: number
  longitude: number
  kw_peak: number
}

type EV = {
  id: number
  ev_name?: string
  kw_peak_loading: number
  kwh_battery: number
}

type BESS = {
  id: number
  name?: string
  kw_peak_charge: number
  kw_peak_discharge: number
  kwh: number
}

type Electricity = {
  id: number
  name: string
  price_typ: "fixed" | "dynamic_EPEX"
  fixed_price?: number | null
  market_zone: string
  is_active: boolean
}

type DowntimeRuleLite = {
  id: number
  ev_id?: number
  weekdays_mask?: number
  start_time: string
  end_time: string
  valid_from?: string | null
  valid_to?: string | null
  soc_target_start_pct?: number | null
  soc_target_end_pct?: number | null
  tz_name?: string
}

type CheckItem = {
  key: string
  label: string
  ok: boolean
  severity: "critical" | "warning"
  hint: string
}

type ScenarioSummary = {
  id: string
  createdAt: string
  status: string
  objective: number
  totalGridImport: number
  totalGridExport: number
  totalDemand: number
  totalEvCharge: number
}

type ConsumptionPayload = {
  annual_consumption_kwh: number
  load_profile_type: "SLP" | "SLP_HEATPUMP"
}

type EVPatchPayload = {
  ev_name?: string
  kw_peak_loading?: number
  kwh_battery?: number
}

type BESSPatchPayload = {
  kw_peak_charge?: number
  kw_peak_discharge?: number
  kwh?: number
}

type DowntimePatchPayload = {
  weekdays_mask: number
  start_time: string
  end_time: string
  valid_from?: string
  valid_to?: string
  soc_target_start_pct?: number
  soc_target_end_pct?: number
  tz_name: string
}

type ChartPoint = {
  index: number
  timestamp: string
  timestampMs: number
  timeLabel: string
  price: number
  pv: number
  demand: number
  evCharge: number
  evSocTotal: number
  gridImport: number
  gridExport: number
  bessCharge: number
  bessDischarge: number
  bessSoc: number
}

type SeriesKey =
  | "price"
  | "pv"
  | "demand"
  | "evCharge"
  | "evSocTotal"
  | "gridImport"
  | "gridExport"
  | "bessCharge"
  | "bessDischarge"
  | "bessSoc"

const SERIES_CONFIG: Array<{ key: SeriesKey; label: string; color: string; rightAxis?: boolean }> = [
  { key: "gridImport", label: "Grid Import (kWh/slot)", color: "#0f766e" },
  { key: "gridExport", label: "Grid Export (kWh/slot)", color: "#f97316" },
  { key: "pv", label: "PV (kWh/slot)", color: "#16a34a" },
  { key: "demand", label: "Demand (kWh/slot)", color: "#dc2626" },
  { key: "evCharge", label: "EV Charge (kWh/slot)", color: "#be185d" },
  { key: "evSocTotal", label: "EV SOC Total (kWh)", color: "#7c2d12" },
  { key: "bessCharge", label: "BESS Charge (kWh/slot)", color: "#0ea5e9" },
  { key: "bessDischarge", label: "BESS Discharge (kWh/slot)", color: "#1d4ed8" },
  { key: "bessSoc", label: "BESS SOC (kWh)", color: "#2563eb" },
  { key: "price", label: "Price", color: "#7c3aed", rightAxis: true },
]

function formatTimeLabel(ts: string): string {
  const date = new Date(ts)
  return new Intl.DateTimeFormat("de-DE", {
    timeZone: "Europe/Berlin",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

function formatBerlinDateTime(ts: string): string {
  const date = new Date(ts)
  return new Intl.DateTimeFormat("de-DE", {
    timeZone: "Europe/Berlin",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

function toInputTime(value: string): string {
  return value.slice(0, 5)
}

const OptimizationPage = () => {
  const token = useMemo(() => localStorage.getItem("access_token") ?? "", [])
  const queryClient = useQueryClient()
  const [result, setResult] = useState<OptimizationResponse | null>(null)
  const [error, setError] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [showFirstHalf, setShowFirstHalf] = useState(false)
  const [showAllTableRows, setShowAllTableRows] = useState(false)
  const [horizonDays, setHorizonDays] = useState<1 | 2>(1)
  const [enforceTerminalBessSoc, setEnforceTerminalBessSoc] = useState(true)
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>(() => {
    try {
      const raw = sessionStorage.getItem("optimization_scenarios")
      return raw ? (JSON.parse(raw) as ScenarioSummary[]) : []
    } catch {
      return []
    }
  })
  const [demandDraft, setDemandDraft] = useState<string>("")
  const [profileDraft, setProfileDraft] = useState<"SLP" | "SLP_HEATPUMP">("SLP")
  const [selectedTariffId, setSelectedTariffId] = useState<number | "">("")
  const [selectedEvInlineId, setSelectedEvInlineId] = useState<number | "">("")
  const [evNameDraft, setEvNameDraft] = useState<string>("")
  const [evKwDraft, setEvKwDraft] = useState<string>("")
  const [evKwhDraft, setEvKwhDraft] = useState<string>("")
  const [selectedBessInlineId, setSelectedBessInlineId] = useState<number | "">("")
  const [bessKwChargeDraft, setBessKwChargeDraft] = useState<string>("")
  const [bessKwDischargeDraft, setBessKwDischargeDraft] = useState<string>("")
  const [bessKwhDraft, setBessKwhDraft] = useState<string>("")
  const [selectedDowntimeRuleId, setSelectedDowntimeRuleId] = useState<number | "">("")
  const [downtimeStartTimeDraft, setDowntimeStartTimeDraft] = useState<string>("")
  const [downtimeEndTimeDraft, setDowntimeEndTimeDraft] = useState<string>("")
  const [downtimeSocStartDraft, setDowntimeSocStartDraft] = useState<string>("")
  const [downtimeSocEndDraft, setDowntimeSocEndDraft] = useState<string>("")
  const [visibleSeries, setVisibleSeries] = useState<Record<SeriesKey, boolean>>({
    price: true,
    pv: true,
    demand: true,
    evCharge: true,
    evSocTotal: false,
    gridImport: true,
    gridExport: true,
    bessCharge: true,
    bessDischarge: true,
    bessSoc: true,
  })

  const me = useQuery<Me, APIError>({
    queryKey: ["me"],
    queryFn: () => getAPI("/api/me", { token, credentials: "include" }),
  })
  const pvs = useQuery<PV[], APIError>({
    queryKey: ["pv"],
    queryFn: () => getAPI("/api/pv", { token, credentials: "include" }),
  })
  const evs = useQuery<EV[], APIError>({
    queryKey: ["ev"],
    queryFn: () => getAPI("/api/ev", { token, credentials: "include" }),
  })
  const bess = useQuery<BESS[], APIError>({
    queryKey: ["bess"],
    queryFn: () => getAPI("/api/bess", { token, credentials: "include" }),
  })
  const tariffs = useQuery<Electricity[], APIError>({
    queryKey: ["electricity"],
    queryFn: () => getAPI("/api/electricity", { token, credentials: "include" }),
  })

  const downtimeRules = useQuery<Record<number, DowntimeRuleLite[]>, APIError>({
    queryKey: ["ev-downtime-rules", (evs.data ?? []).map((ev) => ev.id).join(",")],
    enabled: Boolean(evs.data?.length),
    queryFn: async () => {
      const list = evs.data ?? []
      const pairs = await Promise.all(
        list.map(async (ev) => {
          const rules = await getAPI<DowntimeRuleLite[]>(`/api/ev/${ev.id}/downtime-rules`, {
            token,
            credentials: "include",
          })
          return [ev.id, rules] as const
        })
      )
      return Object.fromEntries(pairs)
    },
  })

  const activeTariff = useMemo(
    () => tariffs.data?.find((tariff) => tariff.is_active) ?? null,
    [tariffs.data]
  )

  const selectedInlineEv = useMemo(
    () => (evs.data ?? []).find((ev) => ev.id === selectedEvInlineId) ?? null,
    [evs.data, selectedEvInlineId]
  )

  const selectedInlineBess = useMemo(
    () => (bess.data ?? []).find((item) => item.id === selectedBessInlineId) ?? null,
    [bess.data, selectedBessInlineId]
  )

  const selectedEvRules = useMemo(
    () => (selectedEvInlineId ? downtimeRules.data?.[selectedEvInlineId] ?? [] : []),
    [selectedEvInlineId, downtimeRules.data]
  )

  const selectedDowntimeRule = useMemo(
    () => selectedEvRules.find((rule) => rule.id === selectedDowntimeRuleId) ?? null,
    [selectedEvRules, selectedDowntimeRuleId]
  )

  useEffect(() => {
    if (!me.data) return
    setDemandDraft(String(me.data.annual_consumption_kwh ?? ""))
    setProfileDraft(me.data.load_profile_type ?? "SLP")
  }, [me.data])

  useEffect(() => {
    if (!tariffs.data?.length) {
      setSelectedTariffId("")
      return
    }
    const active = tariffs.data.find((t) => t.is_active)
    if (active) {
      setSelectedTariffId(active.id)
      return
    }
    setSelectedTariffId((prev) => (prev === "" ? tariffs.data[0].id : prev))
  }, [tariffs.data])

  useEffect(() => {
    if (!evs.data?.length) {
      setSelectedEvInlineId("")
      return
    }
    setSelectedEvInlineId((prev) => (prev === "" ? evs.data[0].id : prev))
  }, [evs.data])

  useEffect(() => {
    if (!selectedInlineEv) {
      setEvNameDraft("")
      setEvKwDraft("")
      setEvKwhDraft("")
      return
    }
    setEvNameDraft(selectedInlineEv.ev_name ?? "")
    setEvKwDraft(String(selectedInlineEv.kw_peak_loading))
    setEvKwhDraft(String(selectedInlineEv.kwh_battery))
  }, [selectedInlineEv])

  useEffect(() => {
    if (!bess.data?.length) {
      setSelectedBessInlineId("")
      return
    }
    setSelectedBessInlineId((prev) => (prev === "" ? bess.data[0].id : prev))
  }, [bess.data])

  useEffect(() => {
    if (!selectedInlineBess) {
      setBessKwChargeDraft("")
      setBessKwDischargeDraft("")
      setBessKwhDraft("")
      return
    }
    setBessKwChargeDraft(String(selectedInlineBess.kw_peak_charge))
    setBessKwDischargeDraft(String(selectedInlineBess.kw_peak_discharge))
    setBessKwhDraft(String(selectedInlineBess.kwh))
  }, [selectedInlineBess])

  useEffect(() => {
    if (!selectedEvRules.length) {
      setSelectedDowntimeRuleId("")
      return
    }
    setSelectedDowntimeRuleId((prev) => (prev === "" ? selectedEvRules[0].id : prev))
  }, [selectedEvRules])

  useEffect(() => {
    if (!selectedDowntimeRule) {
      setDowntimeStartTimeDraft("")
      setDowntimeEndTimeDraft("")
      setDowntimeSocStartDraft("")
      setDowntimeSocEndDraft("")
      return
    }
    setDowntimeStartTimeDraft(toInputTime(selectedDowntimeRule.start_time))
    setDowntimeEndTimeDraft(toInputTime(selectedDowntimeRule.end_time))
    setDowntimeSocStartDraft(
      selectedDowntimeRule.soc_target_start_pct === null || selectedDowntimeRule.soc_target_start_pct === undefined
        ? ""
        : String(selectedDowntimeRule.soc_target_start_pct)
    )
    setDowntimeSocEndDraft(
      selectedDowntimeRule.soc_target_end_pct === null || selectedDowntimeRule.soc_target_end_pct === undefined
        ? ""
        : String(selectedDowntimeRule.soc_target_end_pct)
    )
  }, [selectedDowntimeRule])

  useEffect(() => {
    sessionStorage.setItem("optimization_scenarios", JSON.stringify(scenarios))
  }, [scenarios])

  const saveDemandMutation = useMutation<Me, APIError, ConsumptionPayload>({
    mutationFn: (payload) =>
      patchAPI<Me>("/api/me/consumption", payload, {
        token,
        credentials: "include",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["me"] })
    },
  })

  const activateTariffMutation = useMutation<unknown, APIError, number>({
    mutationFn: (tariffId) =>
      patchAPI(`/api/electricity/${tariffId}`, { is_active: true }, { token, credentials: "include" }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["electricity"] })
    },
  })

  const patchEvMutation = useMutation<unknown, APIError, { evId: number; payload: EVPatchPayload }>({
    mutationFn: ({ evId, payload }) =>
      patchAPI(`/api/ev/${evId}`, payload, {
        token,
        credentials: "include",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["ev"] })
    },
  })

  const patchBessMutation = useMutation<unknown, APIError, { bessId: number; payload: BESSPatchPayload }>({
    mutationFn: ({ bessId, payload }) =>
      patchAPI(`/api/bess/${bessId}`, payload, {
        token,
        credentials: "include",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["bess"] })
    },
  })

  const patchDowntimeMutation = useMutation<
    unknown,
    APIError,
    { evId: number; ruleId: number; payload: DowntimePatchPayload }
  >({
    mutationFn: ({ evId, ruleId, payload }) =>
      patchAPI(`/api/ev/${evId}/downtime-rules/${ruleId}`, payload, {
        token,
        credentials: "include",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["ev-downtime-rules"] })
    },
  })

  const inputSummary = useMemo(() => {
    const totalPvKwPeak = (pvs.data ?? []).reduce((sum, item) => sum + item.kw_peak, 0)
    const totalEvCapacity = (evs.data ?? []).reduce((sum, item) => sum + item.kwh_battery, 0)
    const totalEvChargePower = (evs.data ?? []).reduce((sum, item) => sum + item.kw_peak_loading, 0)
    const totalBessCapacity = (bess.data ?? []).reduce((sum, item) => sum + item.kwh, 0)
    return {
      totalPvKwPeak,
      totalEvCapacity,
      totalEvChargePower,
      totalBessCapacity,
    }
  }, [bess.data, evs.data, pvs.data])

  const preRunChecks = useMemo<CheckItem[]>(() => {
    const allRules = Object.values(downtimeRules.data ?? {}).flat()
    const hasUnusualTripTarget = allRules.some((rule) => {
      if (rule.soc_target_start_pct === null || rule.soc_target_start_pct === undefined) return false
      if (rule.soc_target_end_pct === null || rule.soc_target_end_pct === undefined) return false
      return rule.soc_target_end_pct > rule.soc_target_start_pct
    })

    return [
      {
        key: "tariff",
        label: "Active tariff selected",
        ok: Boolean(activeTariff),
        severity: "critical",
        hint: "Set one electricity tariff as active.",
      },
      {
        key: "demand",
        label: "Demand profile configured",
        ok: Boolean(me.data && me.data.annual_consumption_kwh > 0),
        severity: "critical",
        hint: "Set annual consumption and load profile in Demand Profile form.",
      },
      {
        key: "ev",
        label: "At least one EV available",
        ok: (evs.data?.length ?? 0) > 0,
        severity: "critical",
        hint: "Create at least one EV before running optimization.",
      },
      {
        key: "bess",
        label: "Battery available (recommended)",
        ok: (bess.data?.length ?? 0) > 0,
        severity: "warning",
        hint: "Add a BESS to improve shifting and reduce expensive import.",
      },
      {
        key: "downtime-targets",
        label: "Downtime SOC targets look plausible",
        ok: !hasUnusualTripTarget,
        severity: "warning",
        hint: "Some rules have SOC end greater than SOC start. Check if this is intended.",
      },
    ]
  }, [activeTariff, me.data, evs.data, bess.data, downtimeRules.data])

  const hasCriticalFailures = useMemo(
    () => preRunChecks.some((check) => check.severity === "critical" && !check.ok),
    [preRunChecks]
  )

  const conflictHints = useMemo(() => {
    const hints: string[] = []

    for (const check of preRunChecks) {
      if (!check.ok) {
        hints.push(`${check.label}: ${check.hint}`)
      }
    }

    if (result && result.status !== "Optimal") {
      hints.push("Solver status is not Optimal. This often indicates conflicting constraints.")
      for (const item of result.day_advice?.items ?? []) {
        hints.push(item)
      }
    }

    return Array.from(new Set(hints))
  }, [preRunChecks, result])

  const evMovement = useMemo(() => {
    if (!result) return []

    return result.ev.map((ev) => {
      const segments: Array<{
        startIdx: number
        endIdx: number
        startSoc: number
        endSoc: number
      }> = []

      let startIdx: number | null = null
      for (let i = 0; i < ev.available.length; i += 1) {
        const isUnavailable = !ev.available[i]
        const prevUnavailable = i > 0 ? !ev.available[i - 1] : false
        const nextUnavailable = i < ev.available.length - 1 ? !ev.available[i + 1] : false

        if (isUnavailable && !prevUnavailable) {
          startIdx = i
        }
        if (isUnavailable && !nextUnavailable && startIdx !== null) {
          segments.push({
            startIdx,
            endIdx: i,
            startSoc: ev.kwh_soc[startIdx] ?? 0,
            endSoc: ev.kwh_soc[i] ?? 0,
          })
          startIdx = null
        }
      }

      return {
        evId: ev.ev_id,
        name: evs.data?.find((item) => item.id === ev.ev_id)?.ev_name || `EV ${ev.ev_id}`,
        segments,
      }
    })
  }, [result, evs.data])

  const chartData = useMemo<ChartPoint[]>(() => {
    if (!result) return []

    return result.timestamps.map((timestamp, idx) => ({
      evCharge: result.ev.reduce((sum, ev) => sum + (ev.kwh_charge[idx] ?? 0), 0),
      evSocTotal: result.ev.reduce((sum, ev) => sum + (ev.kwh_soc[idx] ?? 0), 0),
      index: idx,
      timestamp,
      timestampMs: new Date(timestamp).getTime(),
      timeLabel: formatTimeLabel(timestamp),
      price: result.prices[idx] ?? 0,
      pv: result.kwh_pv[idx] ?? 0,
      demand: result.kwh_demand[idx] ?? 0,
      gridImport: result.kwh_grid_entnahme[idx] ?? 0,
      gridExport: result.kwh_grid_einspeisung[idx] ?? 0,
      bessCharge: result.kwh_bess_charge[idx] ?? 0,
      bessDischarge: result.kwh_bess_discharge[idx] ?? 0,
      bessSoc: result.kwh_bess_soc[idx] ?? 0,
    }))
  }, [result])

  const outputRows = useMemo(() => {
    if (!result) return []
    return result.timestamps.map((timestamp, idx) => ({
      timestamp,
      price: result.prices[idx] ?? 0,
      demand: result.kwh_demand[idx] ?? 0,
      pv: result.kwh_pv[idx] ?? 0,
      gridImport: result.kwh_grid_entnahme[idx] ?? 0,
      gridExport: result.kwh_grid_einspeisung[idx] ?? 0,
      bessCharge: result.kwh_bess_charge[idx] ?? 0,
      bessDischarge: result.kwh_bess_discharge[idx] ?? 0,
      bessSoc: result.kwh_bess_soc[idx] ?? 0,
    }))
  }, [result])

  const shownRows = useMemo(
    () => (showAllTableRows ? outputRows : outputRows.slice(0, 24)),
    [outputRows, showAllTableRows]
  )

  const shownChartData = useMemo(
    () => (showFirstHalf ? chartData.slice(0, 48) : chartData),
    [chartData, showFirstHalf]
  )

  const summary = useMemo(() => {
    if (!result) return null

    const totalImport = result.kwh_grid_entnahme.reduce((sum, value) => sum + value, 0)
    const totalExport = result.kwh_grid_einspeisung.reduce((sum, value) => sum + value, 0)
    const totalPv = result.kwh_pv.reduce((sum, value) => sum + value, 0)
    const totalDemand = result.kwh_demand.reduce((sum, value) => sum + value, 0)
    const totalEvCharge = result.ev.reduce(
      (sum, ev) => sum + ev.kwh_charge.reduce((evSum, value) => evSum + value, 0),
      0
    )
    const totalBessCharge = result.kwh_bess_charge.reduce((sum, value) => sum + value, 0)
    const totalBessDischarge = result.kwh_bess_discharge.reduce((sum, value) => sum + value, 0)
    const endSoc = result.kwh_bess_soc[result.kwh_bess_soc.length - 1] ?? 0

    return {
      totalImport,
      totalExport,
      totalPv,
      totalDemand,
      totalEvCharge,
      totalBessCharge,
      totalBessDischarge,
      endSoc,
    }
  }, [result])

  async function runOptimization() {
    setError("")
    if (hasCriticalFailures) {
      setError("Pre-run validation failed. Check the checklist below.")
      return
    }
    setLoading(true)
    try {
      const res = await postAPI<OptimizationResponse>(
        `/api/optimization/day_ahead?horizon_days=${horizonDays}&enforce_terminal_bess_soc=${enforceTerminalBessSoc}`,
        undefined,
        {
        token,
        credentials: "include",
        timeoutMs: 45000,
        }
      )
      setResult(res)
      const scenario: ScenarioSummary = {
        id: `${Date.now()}`,
        createdAt: new Date().toISOString(),
        status: res.status,
        objective: res.objective,
        totalGridImport: res.kwh_grid_entnahme.reduce((sum, value) => sum + value, 0),
        totalGridExport: res.kwh_grid_einspeisung.reduce((sum, value) => sum + value, 0),
        totalDemand: res.kwh_demand.reduce((sum, value) => sum + value, 0),
        totalEvCharge: res.ev.reduce(
          (sum, ev) => sum + ev.kwh_charge.reduce((evSum, value) => evSum + value, 0),
          0
        ),
      }
      setScenarios((prev) => [scenario, ...prev].slice(0, 3))
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Optimization failed")
    } finally {
      setLoading(false)
    }
  }

  async function fetchAllForecasts() {
    setError("")
    try {
      const res = await postAPI<unknown>("/api/forecastPV/", undefined, {
        token,
        credentials: "include",
      })
      console.log("forecast", res)
      alert("Forecast fetched. Check browser console for payload.")
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Forecast fetch failed")
    }
  }

  function toggleSeries(series: SeriesKey) {
    setVisibleSeries((prev) => ({ ...prev, [series]: !prev[series] }))
  }

  async function handleSaveDemandInline() {
    setError("")
    const annual = Number(demandDraft)
    if (!Number.isFinite(annual) || annual <= 0) {
      setError("Annual consumption must be a number > 0.")
      return
    }
    try {
      await saveDemandMutation.mutateAsync({
        annual_consumption_kwh: annual,
        load_profile_type: profileDraft,
      })
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Saving demand profile failed")
    }
  }

  async function handleSetActiveTariffInline() {
    setError("")
    if (!selectedTariffId) {
      setError("Select a tariff first.")
      return
    }
    try {
      await activateTariffMutation.mutateAsync(selectedTariffId)
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Setting active tariff failed")
    }
  }

  async function refreshInputSnapshot() {
    setError("")
    try {
      await Promise.all([
        me.refetch(),
        pvs.refetch(),
        evs.refetch(),
        bess.refetch(),
        tariffs.refetch(),
        downtimeRules.refetch(),
      ])
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Refreshing input snapshot failed")
    }
  }

  async function handleSaveEvInline() {
    setError("")
    if (!selectedEvInlineId) {
      setError("Select an EV first.")
      return
    }
    const kw = Number(evKwDraft)
    const kwh = Number(evKwhDraft)
    if (!Number.isFinite(kw) || kw <= 0 || !Number.isFinite(kwh) || kwh <= 0) {
      setError("EV charging power and battery capacity must be numbers > 0.")
      return
    }
    try {
      await patchEvMutation.mutateAsync({
        evId: selectedEvInlineId,
        payload: {
          ev_name: evNameDraft || undefined,
          kw_peak_loading: kw,
          kwh_battery: kwh,
        },
      })
      await downtimeRules.refetch()
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Saving EV failed")
    }
  }

  async function handleSaveBessInline() {
    setError("")
    if (!selectedBessInlineId) {
      setError("Select a BESS first.")
      return
    }
    const kwCharge = Number(bessKwChargeDraft)
    const kwDischarge = Number(bessKwDischargeDraft)
    const kwh = Number(bessKwhDraft)
    if (
      !Number.isFinite(kwCharge) ||
      kwCharge <= 0 ||
      !Number.isFinite(kwDischarge) ||
      kwDischarge <= 0 ||
      !Number.isFinite(kwh) ||
      kwh <= 0
    ) {
      setError("BESS charge/discharge power and capacity must be numbers > 0.")
      return
    }
    try {
      await patchBessMutation.mutateAsync({
        bessId: selectedBessInlineId,
        payload: {
          kw_peak_charge: kwCharge,
          kw_peak_discharge: kwDischarge,
          kwh,
        },
      })
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Saving BESS failed")
    }
  }

  async function handleSaveDowntimeInline() {
    setError("")
    if (!selectedEvInlineId || !selectedDowntimeRule) {
      setError("Select EV and downtime rule first.")
      return
    }

    const socStart = downtimeSocStartDraft ? Number(downtimeSocStartDraft) : undefined
    const socEnd = downtimeSocEndDraft ? Number(downtimeSocEndDraft) : undefined

    if (socStart !== undefined && (!Number.isFinite(socStart) || socStart < 0 || socStart > 100)) {
      setError("SOC start target must be between 0 and 100.")
      return
    }
    if (socEnd !== undefined && (!Number.isFinite(socEnd) || socEnd < 0 || socEnd > 100)) {
      setError("SOC end target must be between 0 and 100.")
      return
    }

    try {
      await patchDowntimeMutation.mutateAsync({
        evId: selectedEvInlineId,
        ruleId: selectedDowntimeRule.id,
        payload: {
          weekdays_mask: selectedDowntimeRule.weekdays_mask ?? 62,
          start_time: downtimeStartTimeDraft || toInputTime(selectedDowntimeRule.start_time),
          end_time: downtimeEndTimeDraft || toInputTime(selectedDowntimeRule.end_time),
          valid_from: selectedDowntimeRule.valid_from ?? undefined,
          valid_to: selectedDowntimeRule.valid_to ?? undefined,
          soc_target_start_pct: socStart,
          soc_target_end_pct: socEnd,
          tz_name: selectedDowntimeRule.tz_name ?? "Europe/Berlin",
        },
      })
      await downtimeRules.refetch()
    } catch (err) {
      setError(err instanceof APIError ? err.message : "Saving downtime rule failed")
    }
  }

  return (
    <section className="mx-auto max-w-6xl space-y-4 text-left">
      <h1 className="text-2xl font-semibold text-slate-900">Optimization Tool</h1>
      <div className="rounded-xl border border-slate-200 bg-white p-3">
        <p className="mb-2 text-sm font-semibold text-slate-900">Run Configuration</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[220px_1fr_auto_auto] md:items-end">
          <label className="text-xs text-slate-600">
            Forecast Horizon
            <select
              className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
              value={horizonDays}
              onChange={(e) => {
                const next = Number(e.currentTarget.value) === 2 ? 2 : 1
                setHorizonDays(next)
                if (next === 2) {
                  setEnforceTerminalBessSoc(false)
                }
              }}
            >
              <option value={1}>1 day (96 slots)</option>
              <option value={2}>2 days (192 slots)</option>
            </select>
          </label>
          <label className="inline-flex items-center gap-2 text-xs text-slate-700">
            <input
              type="checkbox"
              checked={enforceTerminalBessSoc}
              onChange={(e) => setEnforceTerminalBessSoc(e.currentTarget.checked)}
            />
            Keep strict BESS end SOC (40%) at horizon end
          </label>
          <button className="rounded-lg bg-slate-900 px-3 py-2 text-white" onClick={runOptimization} disabled={loading}>
            {loading ? "Running..." : "Run Day Ahead"}
          </button>
          <button className="rounded-lg border border-slate-300 px-3 py-2" onClick={fetchAllForecasts}>
            Fetch PV Forecasts
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Tip: for 2-day runs, disable strict end SOC to see the natural operating regime with less terminal constraint distortion.
        </p>
      </div>

      {error && <p className="text-red-600">{error}</p>}

      <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">Pre-Run Validation</h2>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {preRunChecks.map((check) => (
            <div key={check.key} className="rounded border border-slate-200 px-3 py-2 text-xs">
              <p className={`font-semibold ${check.ok ? "text-emerald-700" : check.severity === "critical" ? "text-red-700" : "text-amber-700"}`}>
                {check.ok ? "OK" : check.severity === "critical" ? "Required" : "Recommended"}: {check.label}
              </p>
              {!check.ok ? <p className="text-slate-600">{check.hint}</p> : null}
            </div>
          ))}
        </div>
      </div>

      {conflictHints.length > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50/50 p-4">
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Conflict Explainer</h2>
          <ul className="list-disc space-y-1 pl-4 text-xs text-slate-800">
            {conflictHints.map((hint) => (
              <li key={hint}>{hint}</li>
            ))}
          </ul>
        </div>
      )}

      {scenarios.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="mb-2 text-lg font-semibold text-slate-900">Scenario Compare (Last 3 Runs)</h2>
          <div className="overflow-auto rounded border border-slate-200">
            <table className="min-w-full border-collapse text-xs">
              <thead className="bg-slate-100 text-slate-700">
                <tr>
                  <th className="border-b border-slate-200 px-2 py-1 text-left">Run Time (Berlin)</th>
                  <th className="border-b border-slate-200 px-2 py-1 text-left">Status</th>
                  <th className="border-b border-slate-200 px-2 py-1 text-left">Objective</th>
                  <th className="border-b border-slate-200 px-2 py-1 text-left">Grid Import</th>
                  <th className="border-b border-slate-200 px-2 py-1 text-left">Grid Export</th>
                  <th className="border-b border-slate-200 px-2 py-1 text-left">Demand</th>
                  <th className="border-b border-slate-200 px-2 py-1 text-left">EV Charge</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.map((scenario) => (
                  <tr key={scenario.id} className="odd:bg-white even:bg-slate-50">
                    <td className="border-b border-slate-200 px-2 py-1">{formatBerlinDateTime(scenario.createdAt)}</td>
                    <td className="border-b border-slate-200 px-2 py-1">{scenario.status}</td>
                    <td className="border-b border-slate-200 px-2 py-1">{scenario.objective.toFixed(3)}</td>
                    <td className="border-b border-slate-200 px-2 py-1">{scenario.totalGridImport.toFixed(3)}</td>
                    <td className="border-b border-slate-200 px-2 py-1">{scenario.totalGridExport.toFixed(3)}</td>
                    <td className="border-b border-slate-200 px-2 py-1">{scenario.totalDemand.toFixed(3)}</td>
                    <td className="border-b border-slate-200 px-2 py-1">{scenario.totalEvCharge.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="text-lg font-semibold text-slate-900">Optimization Input Snapshot</h2>
        <p className="text-xs text-slate-500">
          These values are loaded from your backend objects and used by optimization, even though they are not sent manually in this page request.
        </p>

        <div className="rounded-lg border border-blue-200 bg-blue-50/40 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-900">Inline Optimization Input Controls</p>
            <button
              type="button"
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700"
              onClick={refreshInputSnapshot}
            >
              Refresh Snapshot
            </button>
          </div>
          <p className="mb-3 text-xs text-slate-600">Adjust key optimization inputs directly here without leaving this page (scenario compare stays intact).</p>
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold text-slate-800">Demand Profile</p>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
                <label className="text-xs text-slate-600">
                  Annual Demand (kWh/a)
                  <input
                    type="number"
                    min="1"
                    step="1"
                    value={demandDraft}
                    onChange={(e) => setDemandDraft(e.currentTarget.value)}
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  />
                </label>
                <label className="text-xs text-slate-600">
                  Load Profile
                  <select
                    value={profileDraft}
                    onChange={(e) => setProfileDraft(e.currentTarget.value as "SLP" | "SLP_HEATPUMP")}
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  >
                    <option value="SLP">SLP</option>
                    <option value="SLP_HEATPUMP">SLP_HEATPUMP</option>
                  </select>
                </label>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-60"
                  disabled={saveDemandMutation.isPending}
                  onClick={handleSaveDemandInline}
                >
                  {saveDemandMutation.isPending ? "Saving..." : "Save Demand"}
                </button>
                {saveDemandMutation.isSuccess ? <span className="text-xs text-emerald-700">Saved.</span> : null}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold text-slate-800">Active Tariff</p>
              <label className="text-xs text-slate-600">
                Select Tariff
                <select
                  value={selectedTariffId}
                  onChange={(e) => setSelectedTariffId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  disabled={!tariffs.data?.length}
                >
                  {!tariffs.data?.length ? <option value="">No tariffs available</option> : null}
                  {(tariffs.data ?? []).map((tariff) => (
                    <option key={tariff.id} value={tariff.id}>
                      #{tariff.id} {tariff.name || "unnamed"} ({tariff.price_typ}){tariff.is_active ? " [active]" : ""}
                    </option>
                  ))}
                </select>
              </label>
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-60"
                  disabled={activateTariffMutation.isPending || !selectedTariffId}
                  onClick={handleSetActiveTariffInline}
                >
                  {activateTariffMutation.isPending ? "Updating..." : "Set Active Tariff"}
                </button>
                {activateTariffMutation.isSuccess ? <span className="text-xs text-emerald-700">Updated.</span> : null}
              </div>
            </div>
          </div>

          <div className="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold text-slate-800">EV Quick Edit</p>
              <label className="text-xs text-slate-600">
                Select EV
                <select
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  value={selectedEvInlineId}
                  onChange={(e) => setSelectedEvInlineId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
                >
                  {!evs.data?.length ? <option value="">No EV available</option> : null}
                  {(evs.data ?? []).map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      #{ev.id} {ev.ev_name || "unnamed"}
                    </option>
                  ))}
                </select>
              </label>
              <div className="mt-2 space-y-2">
                <input
                  className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  value={evNameDraft}
                  onChange={(e) => setEvNameDraft(e.currentTarget.value)}
                  placeholder="EV name"
                />
                <input
                  className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={evKwDraft}
                  onChange={(e) => setEvKwDraft(e.currentTarget.value)}
                  placeholder="Charge kW"
                />
                <input
                  className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={evKwhDraft}
                  onChange={(e) => setEvKwhDraft(e.currentTarget.value)}
                  placeholder="Battery kWh"
                />
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-60"
                  disabled={patchEvMutation.isPending || !selectedEvInlineId}
                  onClick={handleSaveEvInline}
                >
                  {patchEvMutation.isPending ? "Saving..." : "Save EV"}
                </button>
                {patchEvMutation.isSuccess ? <span className="text-xs text-emerald-700">Saved.</span> : null}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold text-slate-800">BESS Quick Edit</p>
              <label className="text-xs text-slate-600">
                Select BESS
                <select
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  value={selectedBessInlineId}
                  onChange={(e) => setSelectedBessInlineId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
                >
                  {!bess.data?.length ? <option value="">No BESS available</option> : null}
                  {(bess.data ?? []).map((item) => (
                    <option key={item.id} value={item.id}>
                      #{item.id} {item.name || "unnamed"}
                    </option>
                  ))}
                </select>
              </label>
              <div className="mt-2 space-y-2">
                <input
                  className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={bessKwChargeDraft}
                  onChange={(e) => setBessKwChargeDraft(e.currentTarget.value)}
                  placeholder="Charge kW"
                />
                <input
                  className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={bessKwDischargeDraft}
                  onChange={(e) => setBessKwDischargeDraft(e.currentTarget.value)}
                  placeholder="Discharge kW"
                />
                <input
                  className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={bessKwhDraft}
                  onChange={(e) => setBessKwhDraft(e.currentTarget.value)}
                  placeholder="Capacity kWh"
                />
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-60"
                  disabled={patchBessMutation.isPending || !selectedBessInlineId}
                  onClick={handleSaveBessInline}
                >
                  {patchBessMutation.isPending ? "Saving..." : "Save BESS"}
                </button>
                {patchBessMutation.isSuccess ? <span className="text-xs text-emerald-700">Saved.</span> : null}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <p className="mb-2 text-xs font-semibold text-slate-800">Downtime Rule Quick Edit</p>
              <label className="text-xs text-slate-600">
                Select Rule (for selected EV)
                <select
                  className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                  value={selectedDowntimeRuleId}
                  onChange={(e) => setSelectedDowntimeRuleId(e.currentTarget.value ? Number(e.currentTarget.value) : "")}
                  disabled={!selectedEvRules.length}
                >
                  {!selectedEvRules.length ? <option value="">No downtime rules</option> : null}
                  {selectedEvRules.map((rule) => (
                    <option key={rule.id} value={rule.id}>
                      #{rule.id} {toInputTime(rule.start_time)}-{toInputTime(rule.end_time)}
                    </option>
                  ))}
                </select>
              </label>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <label className="text-xs text-slate-600">
                  Start
                  <input
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                    type="time"
                    value={downtimeStartTimeDraft}
                    onChange={(e) => setDowntimeStartTimeDraft(e.currentTarget.value)}
                  />
                </label>
                <label className="text-xs text-slate-600">
                  End
                  <input
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                    type="time"
                    value={downtimeEndTimeDraft}
                    onChange={(e) => setDowntimeEndTimeDraft(e.currentTarget.value)}
                  />
                </label>
                <label className="text-xs text-slate-600">
                  SOC Start %
                  <input
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    value={downtimeSocStartDraft}
                    onChange={(e) => setDowntimeSocStartDraft(e.currentTarget.value)}
                    placeholder="optional"
                  />
                </label>
                <label className="text-xs text-slate-600">
                  SOC End %
                  <input
                    className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    value={downtimeSocEndDraft}
                    onChange={(e) => setDowntimeSocEndDraft(e.currentTarget.value)}
                    placeholder="optional"
                  />
                </label>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs text-white disabled:opacity-60"
                  disabled={patchDowntimeMutation.isPending || !selectedEvInlineId || !selectedDowntimeRule}
                  onClick={handleSaveDowntimeInline}
                >
                  {patchDowntimeMutation.isPending ? "Saving..." : "Save Rule"}
                </button>
                {patchDowntimeMutation.isSuccess ? <span className="text-xs text-emerald-700">Saved.</span> : null}
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 md:grid-cols-3 xl:grid-cols-6">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Load Profile</p>
            <p className="text-sm font-semibold text-slate-900">{me.data?.load_profile_type ?? "-"}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Annual Demand</p>
            <p className="text-sm font-semibold text-slate-900">
              {me.data ? `${me.data.annual_consumption_kwh.toFixed(0)} kWh/a` : "-"}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Active Tariff</p>
            <p className="text-sm font-semibold text-slate-900">{activeTariff?.name ?? "none"}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">PV Attached</p>
            <p className="text-sm font-semibold text-slate-900">{(pvs.data ?? []).length} ({inputSummary.totalPvKwPeak.toFixed(2)} kWp)</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">EV Attached</p>
            <p className="text-sm font-semibold text-slate-900">
              {(evs.data ?? []).length} ({inputSummary.totalEvCapacity.toFixed(1)} kWh)
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-xs text-slate-500">BESS Attached</p>
            <p className="text-sm font-semibold text-slate-900">{(bess.data ?? []).length} ({inputSummary.totalBessCapacity.toFixed(1)} kWh)</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-3">
            <p className="mb-2 text-xs font-semibold text-slate-800">Selected Tariff</p>
            {activeTariff ? (
              <ul className="space-y-1 text-xs text-slate-700">
                <li>Name: {activeTariff.name}</li>
                <li>Type: {activeTariff.price_typ}</li>
                <li>Market Zone: {activeTariff.market_zone}</li>
                <li>Fixed Price: {activeTariff.fixed_price ?? "dynamic"}</li>
              </ul>
            ) : (
              <p className="text-xs text-red-600">No active tariff found. Optimization will fail until one tariff is active.</p>
            )}
          </div>

          <div className="rounded-lg border border-slate-200 p-3">
            <p className="mb-2 text-xs font-semibold text-slate-800">Attached EVs</p>
            {(evs.data ?? []).length ? (
              <ul className="space-y-1 text-xs text-slate-700">
                {(evs.data ?? []).map((ev) => (
                  <li key={ev.id}>
                    #{ev.id} {ev.ev_name || "unnamed"} | {ev.kw_peak_loading} kW | {ev.kwh_battery} kWh
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-500">No EV attached.</p>
            )}
          </div>
        </div>

        {(me.error || pvs.error || evs.error || bess.error || tariffs.error) && (
          <p className="text-xs text-red-600">
            {me.error?.message || pvs.error?.message || evs.error?.message || bess.error?.message || tariffs.error?.message}
          </p>
        )}
      </div>

      <p className="text-xs text-slate-500">Time axis and tooltip are shown in Europe/Berlin (Germany).</p>

      {result && (
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-4">
          {result.day_advice && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/40 p-3">
              <p className="mb-1 text-sm font-semibold text-slate-900">Day Advice (Rule-Based)</p>
              <p className="mb-2 text-xs text-slate-700">{result.day_advice.summary}</p>
              <ul className="mb-2 list-disc space-y-1 pl-4 text-xs text-slate-800">
                {result.day_advice.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                {Object.entries(result.day_advice.metrics).map(([key, metric]) => (
                  <div key={key} className="rounded border border-amber-100 bg-white px-2 py-1 text-xs text-slate-700">
                    <span className="font-medium">{key}:</span> {metric.toFixed(3)}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-2 md:grid-cols-9">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">Status</p>
              <p className="text-sm font-semibold text-slate-900">{result.status}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">Objective</p>
              <p className="text-sm font-semibold text-slate-900">{result.objective.toFixed(2)}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">Grid Import</p>
              <p className="text-sm font-semibold text-slate-900">{summary?.totalImport.toFixed(2)} kWh</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">Grid Export</p>
              <p className="text-sm font-semibold text-slate-900">{summary?.totalExport.toFixed(2)} kWh</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">Demand</p>
              <p className="text-sm font-semibold text-slate-900">{summary?.totalDemand.toFixed(2)} kWh</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">EV Charge</p>
              <p className="text-sm font-semibold text-slate-900">{summary?.totalEvCharge.toFixed(2)} kWh</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">BESS Charge</p>
              <p className="text-sm font-semibold text-slate-900">{summary?.totalBessCharge.toFixed(2)} kWh</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">BESS Discharge</p>
              <p className="text-sm font-semibold text-slate-900">{summary?.totalBessDischarge.toFixed(2)} kWh</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs text-slate-500">End BESS SOC</p>
              <p className="text-sm font-semibold text-slate-900">{summary?.endSoc.toFixed(2)} kWh</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs text-slate-700"
              onClick={() => setShowFirstHalf((value) => !value)}
            >
              {showFirstHalf ? "Show Full Day" : "Show 00:00-12:00"}
            </button>
            {SERIES_CONFIG.map((series) => (
              <button
                key={series.key}
                type="button"
                onClick={() => toggleSeries(series.key)}
                className={`rounded-lg border px-3 py-1.5 text-xs ${
                  visibleSeries[series.key]
                    ? "border-slate-900 bg-slate-900 text-white"
                    : "border-slate-300 text-slate-700"
                }`}
              >
                {series.label}
              </button>
            ))}
          </div>

          <div className="h-[440px] w-full rounded-lg border border-slate-200 bg-white p-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={shownChartData} margin={{ top: 16, right: 24, left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="timestampMs"
                  type="number"
                  scale="time"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(value: number) =>
                    new Intl.DateTimeFormat("de-DE", {
                      timeZone: "Europe/Berlin",
                      hour: "2-digit",
                      minute: "2-digit",
                    }).format(new Date(value))
                  }
                  minTickGap={20}
                  tick={{ fontSize: 11, fill: "#475569" }}
                />
                <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "#475569" }} width={58} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "#6d28d9" }} width={58} />
                <Tooltip
                  formatter={(value, name) => {
                    const formatted = typeof value === "number" ? value.toFixed(3) : String(value ?? "")
                    return [formatted, String(name)]
                  }}
                  labelFormatter={(_label, payload) => {
                    const rawTimestamp = payload?.[0]?.payload?.timestamp
                    return rawTimestamp ? formatBerlinDateTime(rawTimestamp) : ""
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                {SERIES_CONFIG.map((series) =>
                  visibleSeries[series.key] ? (
                    <Line
                      key={series.key}
                      yAxisId={series.rightAxis ? "right" : "left"}
                      type="linear"
                      dataKey={series.key}
                      name={series.label}
                      stroke={series.color}
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                    />
                  ) : null
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="rounded-lg border border-slate-200 p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-900">Full Model Output by Timestamp</p>
              <button
                type="button"
                className="rounded-lg border border-slate-300 px-2 py-1 text-xs text-slate-700"
                onClick={() => setShowAllTableRows((v) => !v)}
              >
                {showAllTableRows ? "Show first 24 rows" : "Show all 96 rows"}
              </button>
            </div>
            <div className="overflow-auto rounded border border-slate-200">
              <table className="min-w-full border-collapse text-xs">
                <thead className="bg-slate-100 text-slate-700">
                  <tr>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">Berlin Time</th>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">Price</th>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">Demand</th>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">PV</th>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">Grid In</th>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">Grid Out</th>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">BESS Chg</th>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">BESS Dischg</th>
                    <th className="border-b border-slate-200 px-2 py-1 text-left">BESS SOC</th>
                    {result.ev.map((ev) => (
                      <th key={`avail-${ev.ev_id}`} className="border-b border-slate-200 px-2 py-1 text-left">EV {ev.ev_id} Avail</th>
                    ))}
                    {result.ev.map((ev) => (
                      <th key={`chg-${ev.ev_id}`} className="border-b border-slate-200 px-2 py-1 text-left">EV {ev.ev_id} Chg</th>
                    ))}
                    {result.ev.map((ev) => (
                      <th key={`soc-${ev.ev_id}`} className="border-b border-slate-200 px-2 py-1 text-left">EV {ev.ev_id} SOC</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {shownRows.map((row, idx) => (
                    <tr key={row.timestamp} className="odd:bg-white even:bg-slate-50">
                      <td className="border-b border-slate-200 px-2 py-1">{formatBerlinDateTime(row.timestamp)}</td>
                      <td className="border-b border-slate-200 px-2 py-1">{row.price.toFixed(3)}</td>
                      <td className="border-b border-slate-200 px-2 py-1">{row.demand.toFixed(3)}</td>
                      <td className="border-b border-slate-200 px-2 py-1">{row.pv.toFixed(3)}</td>
                      <td className="border-b border-slate-200 px-2 py-1">{row.gridImport.toFixed(3)}</td>
                      <td className="border-b border-slate-200 px-2 py-1">{row.gridExport.toFixed(3)}</td>
                      <td className="border-b border-slate-200 px-2 py-1">{row.bessCharge.toFixed(3)}</td>
                      <td className="border-b border-slate-200 px-2 py-1">{row.bessDischarge.toFixed(3)}</td>
                      <td className="border-b border-slate-200 px-2 py-1">{row.bessSoc.toFixed(3)}</td>
                      {result.ev.map((ev) => (
                        <td key={`avail-${ev.ev_id}-${row.timestamp}`} className="border-b border-slate-200 px-2 py-1">
                          {ev.available[idx] ? "yes" : "no"}
                        </td>
                      ))}
                      {result.ev.map((ev) => (
                        <td key={`chg-${ev.ev_id}-${row.timestamp}`} className="border-b border-slate-200 px-2 py-1">
                          {(ev.kwh_charge[idx] ?? 0).toFixed(3)}
                        </td>
                      ))}
                      {result.ev.map((ev) => (
                        <td key={`soc-${ev.ev_id}-${row.timestamp}`} className="border-b border-slate-200 px-2 py-1">
                          {(ev.kwh_soc[idx] ?? 0).toFixed(3)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 p-3">
            <p className="mb-2 text-sm font-semibold text-slate-900">EV Movement Timeline</p>
            <p className="mb-2 text-xs text-slate-500">Derived from EV availability and SOC around downtime windows.</p>
            <div className="space-y-2">
              {evMovement.map((ev) => (
                <div key={ev.evId} className="rounded border border-slate-200 p-2">
                  <p className="mb-1 text-xs font-semibold text-slate-800">{ev.name} (ID {ev.evId})</p>
                  {ev.segments.length ? (
                    <ul className="list-disc space-y-1 pl-4 text-xs text-slate-700">
                      {ev.segments.map((segment) => (
                        <li key={`${ev.evId}-${segment.startIdx}-${segment.endIdx}`}>
                          {formatBerlinDateTime(result.timestamps[segment.startIdx])} to {formatBerlinDateTime(result.timestamps[segment.endIdx])} | SOC {segment.startSoc.toFixed(2)} kWh {"->"} {segment.endSoc.toFixed(2)} kWh (delta {(segment.endSoc - segment.startSoc).toFixed(2)} kWh)
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500">No downtime movement segments detected in this run.</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export default OptimizationPage
