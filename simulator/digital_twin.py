"""
Motor Digital Twin: Mathematically consistent motor health model for predictive maintenance.

Implements a three-stage degradation model with explicit sensor relationships:
- Stage 0: Healthy plateau (70-85% of life)
- Stage 1: Progressive degradation via power law (crack growth)
- Stage 2: Rapid exponential failure

All sensor values are explicit functions of H_true(t).
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional


class MotorDigitalTwin:
    """
    Digital twin of an induction motor with physics-based degradation.
    
    Parameters
    ----------
    motor_id : str
        Unique identifier for this motor instance
    random_state : int, optional
        Random seed for reproducibility
    
    Lifespan parameters:
    mean_life_hours : float
        Mean total life in hours for lognormal distribution
    std_life_hours : float
        Standard deviation for lognormal distribution
    min_life_hours : float
        Minimum clipped life
    max_life_hours : float
        Maximum clipped life
    
    Stage fractions:
    stage0_fraction : float
        Fraction of life in healthy plateau (0.70-0.85)
    stage1_fraction : float
        Fraction of life at end of Stage 1 (e.g., 0.95)
    
    Degradation parameters:
    power_law_exp_min : float
        Minimum power law exponent b for Stage 1 (1.5-3.5)
    power_law_exp_max : float
        Maximum power law exponent b
    H_min : float
        Healthy baseline health (≈ 0.05)
    H_mid : float
        Health at end of Stage 1 (≈ 0.5)
    
    Sensor noise levels:
    sigma_vib : float
        Vibration RMS noise std
    sigma_kurt : float
        Kurtosis noise std
    sigma_crest : float
        Crest factor noise std
    sigma_temp : float
        Temperature noise std
    sigma_thd : float
        THD noise std
    sigma_rpm : float
        RPM noise std
    
    Sensor ranges:
    RMS_healthy : float
        Healthy vibration RMS (m/s^2)
    RMS_failure : float
        Failure vibration RMS
    Kurt_healthy : float
        Healthy kurtosis
    Kurt_failure : float
        Failure kurtosis
    Crest_healthy : float
        Healthy crest factor
    Crest_failure : float
        Failure crest factor
    T_env : float
        Ambient temperature (°C)
    T_baseline : float
        Healthy operating temperature
    T_crit : float
        Critical temperature threshold
    THD_healthy : float
        Healthy THD (0.05 = 5%)
    THD_failure : float
        Failure THD (0.15 = 15%)
    rated_rpm : float
        Rated motor RPM
    slip_base : float
        Baseline slip fraction
    slip_extra : float
        Additional slip per health degradation
    
    Fusion weights:
    w_vib : float
        Weight for vibration in fused health (0.5)
    w_temp : float
        Weight for temperature (0.3)
    w_curr : float
        Weight for current/THD (0.15)
    w_trend : float
        Weight for trend (0.05)
    """
    
    def __init__(
        self,
        motor_id: str = "M001",
        random_state: Optional[int] = None,
        # Lifespan
        mean_life_hours: float = 2000.0,
        std_life_hours: float = 600.0,
        min_life_hours: float = 1000.0,
        max_life_hours: float = 3000.0,
        # Stage fractions
        stage0_fraction: float = 0.75,
        stage1_fraction: float = 0.95,
        # Degradation
        power_law_exp_min: float = 1.5,
        power_law_exp_max: float = 3.5,
        H_min: float = 0.05,
        H_mid: float = 0.5,
        # Sensor noise
        sigma_vib: float = 0.1,
        sigma_kurt: float = 0.3,
        sigma_crest: float = 0.1,
        sigma_temp: float = 2.0,
        sigma_thd: float = 0.005,
        sigma_rpm: float = 5.0,
        # Sensor ranges
        RMS_healthy: float = 0.8,
        RMS_failure: float = 7.0,
        Kurt_healthy: float = 3.0,
        Kurt_failure: float = 13.0,
        Crest_healthy: float = 2.0,
        Crest_failure: float = 6.0,
        T_env: float = 25.0,
        T_baseline: float = 45.0,
        T_crit: float = 80.0,
        THD_healthy: float = 0.05,
        THD_failure: float = 0.15,
        rated_rpm: float = 1500.0,
        slip_base: float = 0.02,
        slip_extra: float = 0.03,
        # Fusion weights
        w_vib: float = 0.5,
        w_temp: float = 0.3,
        w_curr: float = 0.15,
        w_trend: float = 0.05
    ):
        self.motor_id = motor_id
        self.rng = np.random.RandomState(random_state)
        
        # Store all parameters
        self.mean_life_hours = mean_life_hours
        self.std_life_hours = std_life_hours
        self.min_life_hours = min_life_hours
        self.max_life_hours = max_life_hours
        
        self.H_min = H_min
        self.H_mid = H_mid
        
        # Sensor noise
        self.sigma_vib = sigma_vib
        self.sigma_kurt = sigma_kurt
        self.sigma_crest = sigma_crest
        self.sigma_temp = sigma_temp
        self.sigma_thd = sigma_thd
        self.sigma_rpm = sigma_rpm
        
        # Sensor ranges
        self.RMS_healthy = RMS_healthy
        self.RMS_failure = RMS_failure
        self.Kurt_healthy = Kurt_healthy
        self.Kurt_failure = Kurt_failure
        self.Crest_healthy = Crest_healthy
        self.Crest_failure = Crest_failure
        self.T_env = T_env
        self.T_baseline = T_baseline
        self.T_crit = T_crit
        self.THD_healthy = THD_healthy
        self.THD_failure = THD_failure
        self.rated_rpm = rated_rpm
        self.slip_base = slip_base
        self.slip_extra = slip_extra
        
        # Fusion weights
        self.w_vib = w_vib
        self.w_temp = w_temp
        self.w_curr = w_curr
        self.w_trend = w_trend
        
        # Sample motor-specific parameters
        self._sample_motor_parameters(stage0_fraction, stage1_fraction, 
                                     power_law_exp_min, power_law_exp_max)
        
        # History for tracking
        self.history = []
        self.current_time = 0.0
        self.last_HI_vib = 0.0  # For trend calculation
        
    def _sample_motor_parameters(
        self, 
        stage0_frac: float,
        stage1_frac: float,
        b_min: float,
        b_max: float
    ):
        """Sample motor-specific lifespan and degradation parameters."""
        # Sample total life from lognormal
        variance = self.std_life_hours ** 2
        mu = np.log(self.mean_life_hours ** 2 / np.sqrt(variance + self.mean_life_hours ** 2))
        sigma = np.sqrt(np.log(1 + variance / (self.mean_life_hours ** 2)))
        
        T_total = self.rng.lognormal(mu, sigma)
        self.T_total = np.clip(T_total, self.min_life_hours, self.max_life_hours)
        
        # Stage boundaries
        self.t1 = stage0_frac * self.T_total
        self.t2 = stage1_frac * self.T_total
        self.t3 = self.T_total
        
        # Sample power law exponent for Stage 1
        self.b = self.rng.uniform(b_min, b_max)
        
        # Calculate coefficient A for Stage 1
        # We want: H_min + A * (t2 - t1)^b = H_mid
        if self.t2 > self.t1:
            self.A = (self.H_mid - self.H_min) / ((self.t2 - self.t1) ** self.b)
        else:
            self.A = 0.0
        
        # Calculate exponential rate k for Stage 2
        # We want: H_mid + (1 - H_mid) * (1 - exp(-k * (t3 - t2))) ≈ 1
        # Solving: 1 - exp(-k * (t3 - t2)) ≈ (1 - H_mid) / (1 - H_mid) = 1
        # So: exp(-k * (t3 - t2)) ≈ 0.01 (reach 99% of range)
        # k = -ln(0.01) / (t3 - t2)
        if self.t3 > self.t2:
            self.k = -np.log(0.01) / (self.t3 - self.t2)
        else:
            self.k = 1.0
    
    def compute_H_true(self, t: float) -> float:
        """
        Compute true health index at time t using three-stage model.
        
        Parameters
        ----------
        t : float
            Time in hours since start
            
        Returns
        -------
        float
            Health index in [0, 1], where 0 = healthy, 1 = failed
        """
        if t < self.t1:
            # Stage 0: Healthy plateau with small noise
            epsilon0 = self.rng.normal(0, 0.01)
            H = self.H_min + epsilon0
            
        elif t < self.t2:
            # Stage 1: Power law degradation
            time_in_stage = t - self.t1
            epsilon1 = self.rng.normal(0, 0.01)
            H = self.H_min + self.A * (time_in_stage ** self.b) + epsilon1
            
        else:
            # Stage 2: Exponential rapid degradation
            time_in_stage = t - self.t2
            epsilon2 = self.rng.normal(0, 0.02)
            H = self.H_mid + (1.0 - self.H_mid) * (1 - np.exp(-self.k * time_in_stage)) + epsilon2
        
        return np.clip(H, 0.0, 1.0)
    
    def compute_vibration_features(self, H: float) -> Tuple[float, float, float, float]:
        """
        Compute vibration features from health index.
        
        Parameters
        ----------
        H : float
            Health index [0, 1]
            
        Returns
        -------
        Tuple[float, float, float, float]
            (RMS, kurtosis, crest_factor, peak)
        """
        # RMS with nonlinear growth (exponent 1.5)
        RMS = self.RMS_healthy + (self.RMS_failure - self.RMS_healthy) * (H ** 1.5)
        RMS += self.rng.normal(0, self.sigma_vib)
        RMS = max(RMS, 0.0)
        
        # Kurtosis (linear growth)
        Kurt = self.Kurt_healthy + (self.Kurt_failure - self.Kurt_healthy) * H
        Kurt += self.rng.normal(0, self.sigma_kurt)
        Kurt = max(Kurt, 1.0)
        
        # Crest factor (linear growth)
        Crest = self.Crest_healthy + (self.Crest_failure - self.Crest_healthy) * H
        Crest += self.rng.normal(0, self.sigma_crest)
        Crest = max(Crest, 1.0)
        
        # Peak value
        Peak = Crest * RMS
        
        return RMS, Kurt, Crest, Peak
    
    def compute_temperature(self, H: float) -> float:
        """
        Compute bearing/housing temperature from health index.
        
        Parameters
        ----------
        H : float
            Health index [0, 1]
            
        Returns
        -------
        float
            Temperature in °C
        """
        if H < 0.2:
            # Healthy range
            T = self.T_baseline + self.rng.normal(0, self.sigma_temp)
            
        elif H < 0.8:
            # Progressive heating
            T = self.T_baseline + ((H - 0.2) / 0.6) * 30.0
            T += self.rng.normal(0, self.sigma_temp * 1.5)
            
        else:
            # Critical heating
            T = self.T_baseline + 30.0 + ((H - 0.8) / 0.2) * 20.0
            T += self.rng.normal(0, self.sigma_temp * 2.5)
        
        return np.clip(T, self.T_env, self.T_crit + 10.0)
    
    def compute_thd(self, H: float, load: float = 0.75) -> float:
        """
        Compute Total Harmonic Distortion from health index.
        
        Parameters
        ----------
        H : float
            Health index [0, 1]
        load : float
            Load factor [0, 1]
            
        Returns
        -------
        float
            THD value [0, 1]
        """
        # Quadratic growth (sensitive to late-stage degradation)
        THD = self.THD_healthy + (self.THD_failure - self.THD_healthy) * (H ** 2)
        
        # Load modulation (higher load -> slightly higher THD)
        THD += 0.01 * (load - 0.75)
        
        THD += self.rng.normal(0, self.sigma_thd)
        
        return np.clip(THD, 0.0, 0.3)
    
    def compute_rpm(self, H: float) -> float:
        """
        Compute motor RPM with slip variation from health index.
        
        Parameters
        ----------
        H : float
            Health index [0, 1]
            
        Returns
        -------
        float
            RPM value
        """
        # Slip increases with degradation
        slip_factor = self.slip_base + self.slip_extra * H
        
        # Noise increases with degradation
        noise_std = self.sigma_rpm * (1.0 + H)
        
        RPM = self.rated_rpm * (1.0 - slip_factor)
        RPM += self.rng.normal(0, noise_std)
        
        return max(RPM, 0.0)
    
    def compute_fused_health(
        self, 
        RMS: float, 
        T: float, 
        THD: float,
        dt: float = 1.0
    ) -> float:
        """
        Compute fused health index from sensor readings.
        
        Parameters
        ----------
        RMS : float
            Vibration RMS
        T : float
            Temperature
        THD : float
            Total Harmonic Distortion
        dt : float
            Time step for trend calculation
            
        Returns
        -------
        float
            Fused health index [0, 1]
        """
        # Normalize each channel to [0, 1]
        HI_vib = (RMS - self.RMS_healthy) / (self.RMS_failure - self.RMS_healthy)
        HI_vib = np.clip(HI_vib, 0.0, 1.0)
        
        HI_temp = (T - self.T_baseline) / (self.T_crit - self.T_baseline)
        HI_temp = np.clip(HI_temp, 0.0, 1.0)
        
        HI_curr = (THD - self.THD_healthy) / (self.THD_failure - self.THD_healthy)
        HI_curr = np.clip(HI_curr, 0.0, 1.0)
        
        # Rate of change (trend)
        if dt > 0:
            dHI_dt = (HI_vib - self.last_HI_vib) / dt
            max_rate = 0.1  # Assume max rate is 0.1 per hour
            HI_trend = np.clip(dHI_dt / max_rate, 0.0, 1.0)
        else:
            HI_trend = 0.0
        
        # Update last value for next iteration
        self.last_HI_vib = HI_vib
        
        # Fused health
        H_meas = (self.w_vib * HI_vib + 
                  self.w_temp * HI_temp + 
                  self.w_curr * HI_curr + 
                  self.w_trend * HI_trend)
        
        return np.clip(H_meas, 0.0, 1.0)
    
    def step(self, dt: float = 1.0, load: float = 0.75) -> Dict:
        """
        Advance simulation by one time step.
        
        Parameters
        ----------
        dt : float
            Time step in hours
        load : float
            Load factor [0, 1]
            
        Returns
        -------
        Dict
            Dictionary with all sensor readings and health indices
        """
        # Compute true health
        H_true = self.compute_H_true(self.current_time)
        
        # Generate sensor values
        RMS, Kurt, Crest, Peak = self.compute_vibration_features(H_true)
        T = self.compute_temperature(H_true)
        THD = self.compute_thd(H_true, load)
        RPM = self.compute_rpm(H_true)
        
        # Compute fused health
        H_meas = self.compute_fused_health(RMS, T, THD, dt)
        
        record = {
            'time_hours': self.current_time,
            'motor_id': self.motor_id,
            'H_true': H_true,
            'H_meas': H_meas,
            'rms_vib': RMS,
            'kurt_vib': Kurt,
            'crest_vib': Crest,
            'peak_vib': Peak,
            'temp_c': T,
            'thd': THD,
            'rpm': RPM,
            'load_pct': load * 100
        }
        
        self.history.append(record)
        self.current_time += dt
        
        return record
    
    def simulate(
        self, 
        duration_hours: float,
        dt: float = 1.0,
        load_profile: Optional[np.ndarray] = None
    ) -> pd.DataFrame:
        """
        Run simulation for specified duration.
        
        Parameters
        ----------
        duration_hours : float
            Total simulation time in hours
        dt : float
            Time step in hours
        load_profile : np.ndarray, optional
            Array of load values [0, 1]. If None, constant 0.75
            
        Returns
        -------
        pd.DataFrame
            Complete time series data
        """
        num_steps = int(duration_hours / dt)
        
        if load_profile is None:
            load_profile = np.full(num_steps, 0.75)
        
        for i in range(num_steps):
            load = load_profile[min(i, len(load_profile) - 1)]
            self.step(dt, load)
        
        return pd.DataFrame(self.history)
    
    def get_dataframe(self) -> pd.DataFrame:
        """Return simulation history as DataFrame."""
        return pd.DataFrame(self.history)
    
    def reset(self):
        """Reset simulation state."""
        self.history = []
        self.current_time = 0.0
        self.last_HI_vib = 0.0
        self._sample_motor_parameters(
            self.t1 / self.T_total if self.T_total > 0 else 0.75,
            self.t2 / self.T_total if self.T_total > 0 else 0.95,
            1.5, 3.5
        )


def simulate_fleet(
    num_motors: int = 10,
    duration_hours: float = 2000.0,
    dt: float = 1.0,
    random_state: Optional[int] = None,
    output_dir: Optional[str] = None
) -> pd.DataFrame:
    """
    Simulate a fleet of motors and optionally save to CSV.
    
    Parameters
    ----------
    num_motors : int
        Number of motors to simulate
    duration_hours : float
        Simulation duration in hours
    dt : float
        Time step in hours
    random_state : int, optional
        Random seed for reproducibility
    output_dir : str, optional
        Directory to save CSV files. If None, no files saved.
        
    Returns
    -------
    pd.DataFrame
        Combined data from all motors
    """
    all_data = []
    
    for i in range(num_motors):
        motor_id = f"M{i+1:03d}"
        seed = random_state + i if random_state is not None else None
        
        twin = MotorDigitalTwin(motor_id=motor_id, random_state=seed)
        df = twin.simulate(duration_hours, dt)
        
        all_data.append(df)
        
        if output_dir:
            import os
            os.makedirs(output_dir, exist_ok=True)
            df.to_csv(os.path.join(output_dir, f"{motor_id}_data.csv"), index=False)
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    if output_dir:
        combined_df.to_csv(os.path.join(output_dir, "fleet_combined.csv"), index=False)
    
    return combined_df
