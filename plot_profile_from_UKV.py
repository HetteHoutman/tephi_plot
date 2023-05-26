import cartopy.crs as ccrs
import matplotlib.pyplot as plt

import thermodynamics as th
from iris_read import *
from plot_profile_from_txt import plot_profile, N_squared, scorer_param

# TODO put general functions in appropriate files
def convert_to_ukv_coords(x, y, in_crs, out_crs):
    """transforms coordinates given in crs in_crs to coordinates in crs out_crs.
    works at least for UKV rotated pole."""
    out_x, out_y = out_crs.transform_point(x, y, in_crs)
    return out_x + 360, out_y

def convert_list_to_ukv_coords(x_list, y_list, in_crs, out_crs):
    return np.array([convert_to_ukv_coords(x, y, in_crs, out_crs) for x, y in zip(x_list, y_list)])

def index_selector(desired_value, array):
    """returns the index of the value in array that is closest to desired_value"""
    return (np.abs(array - desired_value)).argmin()

def uv_to_spddir(u, v):
    """converts u and v wind fields to wind speed and direction. Taken from Peter Clark's code."""
    return np.sqrt(u**2 + v**2),  np.arctan2(u, v)*180/np.pi+180

if __name__ == '__main__':
    # read file and load fields
    indir = '/home/users/sw825517/Documents/ukv_data/'
    filename = indir + 'prodm_op_ukv_20150414_09_004.pp'

    year = filename[-18:-14]
    month = filename[-14:-12]
    day = filename[-12:-10]
    forecast_time = filename[-9:-7]
    h = 12

    u_cube = read_variable(filename, 2, h)
    v_cube = read_variable(filename, 3, h)
    p_theta_cube = read_variable(filename, 408, h)
    T_cube = read_variable(filename, 16004, h)
    q_cube = read_variable(filename, 10, h)

    # only plot certain heights
    min_height = 20
    max_height = 5000
    height = u_cube.coord('level_height').points
    level_mask = (height < max_height) & (height > min_height)
    height = height[level_mask]

    # coordinates given in regular lat lon, convert to model's rotated pole system
    # currently the code just plots the profiles at the nearest T grid point of the model.
    xpos = -10.35
    ypos = 51.9
    lats = T_cube.coord('grid_latitude').points
    lons = T_cube.coord('grid_longitude').points

    crs_latlon = ccrs.PlateCarree()
    # crs_rotated = u_cube.coord('grid_latitude').coord_system.as_cartopy_crs()
    crs_rotated = ccrs.RotatedPole(pole_longitude=177.5, pole_latitude=37.5)

    model_x, model_y = convert_to_ukv_coords(xpos, ypos, crs_latlon, crs_rotated)
    lat_index = index_selector(model_y, lats)
    lon_index = index_selector(model_x, lons)
    true_model_x = lons[lon_index]
    true_model_y = lats[lat_index]

    # calculate theta
    theta_col = th.potential_temperature(T_cube.data[level_mask, lat_index, lon_index],
                                         p_theta_cube.data[level_mask, lat_index, lon_index])

    # interpolate winds onto T grid points (Arakawa C-grid) and convert back to latlon from ukv rotated pole
    u_col = 0.5*(u_cube.data[level_mask, lat_index, lon_index-1] +
                 u_cube.data[level_mask, lat_index, lon_index])
    v_col = 0.5*(v_cube.data[level_mask, lat_index-1, lon_index] +
                 v_cube.data[level_mask, lat_index, lon_index])
    u_latlon, v_latlon = crs_latlon.transform_vectors(crs_rotated, np.full_like(u_col, true_model_x),
                                                      np.full_like(u_col, true_model_y), u_col, v_col)
    spd_col, dir_col = uv_to_spddir(u_latlon, v_latlon)

    # N squared
    N2 = N_squared(theta_col, height)
    N2U2 = N2 / u_col ** 2
    l2 = scorer_param(N2, u_col, height)

    # plot
    fig = plot_profile(l2, height, N2U2, theta_col, spd_col, dir_col)

    true_x, true_y = crs_latlon.transform_point(true_model_x, true_model_y, crs_rotated)
    title = f'UKV ({true_x:.02f}, {true_y:.02f}) on {year}/{month}/{day} at {h} ({forecast_time})'
    plt.suptitle(title)
    plt.tight_layout()
    plt.savefig(f'plots/profile_from_UKV_({true_x:.02f}_{true_y:.02f})_{year}{month}{day}_{h}.png', dpi=300)
    plt.show()