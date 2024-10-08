import sys

import cartopy.crs as ccrs
import iris
import matplotlib.pyplot as plt
from iris.analysis.cartography import rotate_winds

import thermodynamics as th
from cube_processing import read_variable, check_level_heights, add_orography, create_latlon_cube
from met_fns import uv_to_spddir, N_squared, scorer_param
from miscellaneous import convert_to_ukv_coords, index_selector, load_settings
from plot_profile_from_txt import plot_profile

if __name__ == '__main__':
    # read file and load fields
    s = load_settings(sys.argv[1])
    # indir = '/home/users/sw825517/Documents/ukv_data/'
    # filename = indir + 'prodm_op_ukv_20150414_09_004.pp'
    filename = s.reg_file

    # TODO use json parameters here and in the other profile and tephi files
    year = filename[-18:-14]
    month = filename[-14:-12]
    day = filename[-12:-10]
    forecast_time = filename[-9:-7]
    h = s.h

    u_cube = read_variable(filename, 2, h)
    v_cube = read_variable(filename, 3, h)
    p_theta_cube = read_variable(filename, 408, h)
    T_cube = read_variable(filename, 16004, h)
    q_cube = read_variable(filename, 10, h)
    orog_cube = read_variable(s.orog_file, 33, s.orog_h)

    q_cube = check_level_heights(q_cube, T_cube)
    u_cube = u_cube.regrid(T_cube, iris.analysis.Linear())
    v_cube = v_cube.regrid(T_cube, iris.analysis.Linear())

    add_orography(orog_cube, u_cube, v_cube, p_theta_cube, T_cube, q_cube)

    # coordinates given in regular lat lon, convert to model's rotated pole system
    # currently the code just plots the profiles at the nearest T grid point of the model.
    # xpos = -10.35
    # ypos = 51.9
    xpos = s.gc_start[0]
    ypos = s.gc_start[1]

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
    theta_col = th.potential_temperature(T_cube.data[:, lat_index, lon_index],
                                         p_theta_cube.data[:, lat_index, lon_index])

    # rotate winds
    u_rot, v_rot = rotate_winds(u_cube, v_cube, iris.coord_systems.GeogCS(iris.fileformats.pp.EARTH_RADIUS))

    # create columns of speed and direction
    u_col = u_rot[:, lat_index, lon_index]
    v_col = v_rot[:, lat_index, lon_index]
    spd_col, dir_col = uv_to_spddir(u_col.data, v_col.data)

    # only plot certain heights
    min_height = 20
    max_height = 5000
    height = u_col.coord('altitude').points
    level_mask = (height < max_height) & (height > min_height)
    height = height[level_mask]

    # N squared
    N2 = N_squared(theta_col[level_mask], height)
    N2U2 = N2 / u_col.data[level_mask] ** 2
    l2 = scorer_param(N2, u_col.data[level_mask], height)

    # plot
    fig = plot_profile(l2, height, N2U2, theta_col[level_mask], spd_col[level_mask], dir_col[level_mask], figsize=(7,4),
                       xlim=(-5e-5, 5e-5))

    true_x, true_y = crs_latlon.transform_point(true_model_x, true_model_y, crs_rotated)
    title = f'UKV ({true_x:.02f}, {true_y:.02f}) on {year}/{month}/{day} at {h} ({forecast_time})'
    # plt.suptitle(title)
    plt.tight_layout()
    plt.savefig(f'plots/profile_from_UKV_({true_x:.02f}_{true_y:.02f})_{year}{month}{day}_{h}.png', dpi=300)
    plt.show()