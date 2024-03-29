from TMCDriver import TMCDriver

driver = TMCDriver(spi_bus=0, spi_device=0)

print(driver)

driver.close()