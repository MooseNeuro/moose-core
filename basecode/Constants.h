/***
 *    Description:  Physical and mathematical constants used across MOOSE.
 *
 *    Single source of truth for the universal constants. Keep unit annotations
 *    with each value. Values are exposed to Python via pymoose (moose.NA,
 *    moose.PI, ...), so Python and C++ can never drift.
 *
 *    Values follow the 2019 SI redefinition (CODATA 2018): NA, the elementary
 *    charge, and hence F = NA*e and R = NA*k_B are now exact. R_OVER_F is
 *    derived from R and F so it stays consistent with them.
 */

#ifndef MOOSE_CONSTANTS_H
#define MOOSE_CONSTANTS_H

namespace moose
{
namespace consts
{

inline constexpr double PI = 3.14159265358979323846;  // dimensionless
inline constexpr double NA = 6.02214076e23;           // Avogadro, 1/mol (exact)
inline constexpr double FaradayConst = 96485.33212;   // Faraday, C/mol (exact)
inline constexpr double GasConst = 8.314462618;       // R, J/(K.mol) (exact)
inline constexpr double ZeroCelsius = 273.15;         // 0 degC in Kelvin (exact)
inline constexpr double ElementaryCharge = 1.602176634e-19;  // e (proton), C (exact)
inline constexpr double Boltzmann = 1.380649e-23;            // k_B, J/K (exact)

// Consistency (exact under the 2019 SI): FaradayConst == NA*ElementaryCharge,
// GasConst == NA*Boltzmann, and R_OVER_F == Boltzmann/ElementaryCharge.

// R/F = k_B/e, derived from the values above so it matches them exactly.
inline constexpr double R_OVER_F = GasConst / FaradayConst;  // V/K

}  // namespace consts
}  // namespace moose

#endif  // MOOSE_CONSTANTS_H
