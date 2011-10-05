"""

"""

import numpy
from matplotlib import pyplot
from optparse import OptionParser

from amuse.community.mocassin.interface import Mocassin

from amuse.units import units
from amuse.units import nbody_system

from amuse.ext.protodisk import ProtoPlanetaryDisk
from amuse.datamodel import Particle
from amuse.datamodel import Grid
from amuse.io import write_set_to_file



def make_grid(number_of_grid_cells, length, constant_hydrogen_density, inner_radius, outer_radius):
    grid = Grid.create([number_of_grid_cells] * 3, length.as_vector_with_length(3))
    
    grid.radius = grid.position.lengths()
    grid.hydrogen_density = constant_hydrogen_density
    grid.hydrogen_density[grid.radius <= inner_radius] = 0 | units.cm ** -3
    grid.hydrogen_density[grid.radius >= outer_radius] = 0 | units.cm ** -3
    return grid
    
def setup_abundancies(code):
    table = code.abundancies_table()
    for atom in table.keys():
        table[atom] = 0.0
    table['H'] = 1.0
    table['He'] = 0.1
    table['C'] = 2.2e-4
    table['N'] = 4.e-5
    table['O'] = 3.3e-4
    table['Ne'] = 5.e-5
    table['S'] = 9.e-6

def plot_temperature_line(radii, electron_temperatures):
    
    pyplot.figure(figsize=(8,8))
    
    pyplot.scatter(
        radii.value_in(1e17 * units.cm),
        electron_temperatures.value_in(units.K)        
    )
    pyplot.title('electron temperature')
    pyplot.xlabel('10^17 cm')
    pyplot.ylabel('K')
    pyplot.xlim(30, 100)
    pyplot.ylim(5500,7500)
    pyplot.show()
    
def main(number_of_grid_cells = 15):
    inner_radius = 30.0e17 | units.cm
    outer_radius = 95.0e17 | units.cm
    
    hydrogen_density = 100 | units.cm ** -3
    
    star=Particle()
    star.position = [0.0] * 3 | units.AU
    star.temperature = 20000 | units.K
    star.luminosity = 600.5 | 1e37 * units.erg * (units.s**-1)
    
    grid=make_grid(
        number_of_grid_cells = number_of_grid_cells,
        length = outer_radius,
        constant_hydrogen_density = hydrogen_density,
        inner_radius = inner_radius,
        outer_radius = outer_radius
    )
    
    radiative_transfer = Mocassin(debugger="xterm", number_of_workers = 1)
    
    #radiative_transfer.redirect_outputs_to("moc3-out.txt", "moc3-err.txt")
    radiative_transfer.set_input_directory(radiative_transfer.get_default_input_directory())
    radiative_transfer.initialize_code()
    radiative_transfer.set_symmetricXYZ(True)
    
    radiative_transfer.parameters.length_x = outer_radius
    radiative_transfer.parameters.length_y = outer_radius
    radiative_transfer.parameters.length_z = outer_radius
    radiative_transfer.parameters.mesh_size = [number_of_grid_cells]*3
    setup_abundancies(radiative_transfer)
    
    radiative_transfer.parameters.initial_nebular_temperature = 6000.0 | units.K
    radiative_transfer.parameters.high_limit_of_the_frequency_mesh = 15 | units.ryd
    radiative_transfer.parameters.low_limit_of_the_frequency_mesh  = 1.001e-5| units.ryd
    
    radiative_transfer.parameters.maximum_number_of_monte_carlo_iterations = 20
    radiative_transfer.parameters.minimum_convergence_level = 100
    radiative_transfer.parameters.total_number_of_photons = 10000000
    radiative_transfer.parameters.total_number_of_points_in_frequency_mesh = 600
    radiative_transfer.parameters.convergence_limit = 0.09
    radiative_transfer.parameters.number_of_ionisation_stages = 6
    
    radiative_transfer.setup_auto_convergence(0.2, 2.0, 1000000000)
    
    radiative_transfer.commit_parameters()
    radiative_transfer.grid.hydrogen_density = grid.hydrogen_density
    radiative_transfer.commit_grid()
    radiative_transfer.particles.add_particle(star)
    radiative_transfer.commit_particles()
    
    previous_percentage_converged = 0.0
    
    for i in range(20):
        radiative_transfer.step()
        percentage_converged = radiative_transfer.get_percentage_converged()
        print percentage_converged
        
        if percentage_converged >= 0.6:
            break
            
        if i == 1:
            continue
            
        if percentage_converged > 0.95:
            continue
            
        convergence_increase = (percentage_converged-previous_percentage_converged)/previous_percentage_converged
        if convergence_increase < 0.2:
            radiative_transfer.total_number_of_photons *= 2
                    
                    
        
    
    grid.electron_temperature = radiative_transfer.grid.electron_temperature
    
    radius = grid.radius.flatten()
    electron_temperature = grid.electron_temperature.flatten()
    selection = electron_temperature > 0 | units.K
    
    plot_temperature_line(radius[selection], electron_temperature[selection])
    
    write_set_to_file(grid, 'h2region.h5', 'amuse')
    

def new_option_parser():
    result = OptionParser()
    result.add_option(
        "-n", "--gridcells", 
        default = 13,
        dest="number_of_grid_cells",
        help="number of cells in each direction",
        type="int"
    )
    return result
    
if __name__ in ("__main__","__plot__"):
    options, arguments = new_option_parser().parse_args()
    main(**options.__dict__)
    
