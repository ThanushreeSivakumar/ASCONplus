package simulation.cupcarbon;

import project.Project;
import device.DeviceList;
import device.MessageEventList;
import simulation.SimulationInputs;
import simulation.WisenSimulation;
import buildings.BuildingList;
import markers.MarkerList;
import javafx.application.Platform;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.ProgressBar;
import javafx.scene.text.Text;
import cupcarbon.CupCarbonApp;
import cupcarbon.CupCarbonController;
import map.WorldMap;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.concurrent.CountDownLatch;

/**
 * CupCarbonRunner — Automated Headless Execution for CupCarbon Star Scenarios.
 *
 * Runs discrete-event WSN simulation for star_5, star_10, star_25, star_50
 * and updates results/raw/cupcarbon_manual.csv.
 */
public class CupCarbonRunner {
    public static void main(String[] args) throws Exception {
        double simTime = 300.0;
        if (args.length > 0) {
            try {
                simTime = Double.parseDouble(args[0]);
            } catch (NumberFormatException e) {
                simTime = 300.0;
            }
        }

        CountDownLatch latch = new CountDownLatch(1);
        try {
            Platform.startup(() -> latch.countDown());
            latch.await();
        } catch (IllegalStateException e) {
            // Platform already initialized
        }

        // Initialize mock controller to intercept UI callbacks safely
        CupCarbonController ctrl = new CupCarbonController() {
            @Override public void displayShortGoodMessage(String s) {}
            @Override public void displayShortGoodMessage_th(String s) {}
            @Override public void displayShortErrMessage(String s) {}
            @Override public void displayLongErrMessageTh(String s) {}
            @Override public void updateSimulationButtons() {}
        };
        ctrl.saveButton = new Button();
        ctrl.progress = new ProgressBar();
        ctrl.simulationTimeLabel = new Label();
        ctrl.runSimulationButton = new Button();
        ctrl.qRunSimulationButton = new Button();
        ctrl.qStopSimulationButton = new Button();
        ctrl.qRunIoTSimulationButton = new Button();
        ctrl.qStopIoTSimulationButton = new Button();
        ctrl.stlabel = new Label();

        java.lang.reflect.Field textReadyField = CupCarbonController.class.getDeclaredField("textReady");
        textReadyField.setAccessible(true);
        textReadyField.set(ctrl, new Text());

        WorldMap worldMap = new WorldMap();
        java.lang.reflect.Field mapField = CupCarbonController.class.getDeclaredField("map");
        mapField.setAccessible(true);
        mapField.set(ctrl, worldMap);
        CupCarbonApp.cupCarbonController = ctrl;

        File baseDir = new File(System.getProperty("user.dir"));
        File scenariosDir = new File(baseDir, "simulation/cupcarbon/scenarios");
        File csvFile = new File(baseDir, "results/raw/cupcarbon_manual.csv");

        int[] nList = {5, 10, 25, 50};

        System.out.println("Running CupCarbon simulation for N in {5, 10, 25, 50} (sim_time_s=" + simTime + ")...");

        StringBuilder csvContent = new StringBuilder();
        csvContent.append("n_nodes,sim_time_s,sent,received,lost,notes\n");

        for (int n : nList) {
            String projectName = "star_" + n;
            File projectPath = new File(scenariosDir, projectName);

            action.CupActionStack.init();
            Project.reset();
            Project.setProjectName(projectPath.getAbsolutePath(), projectName);
            Project.loadParameters();
            Project.loadSession();

            BuildingList.open(Project.getProjectBuildingPathName());
            MarkerList.open(Project.getProjectMarkerPath());
            DeviceList.open();

            SimulationInputs.simulationTime = simTime;
            SimulationInputs.visualDelay = 0;
            SimulationInputs.arrowsDelay = 0;
            SimulationInputs.mobilityAndEvents = false;

            WisenSimulation sim = new WisenSimulation();
            if (!sim.ready()) {
                System.err.println("Scenario " + projectName + " is NOT ready!");
                continue;
            }

            sim.start_simulation();

            long sent = (long) MessageEventList.numberOfSentMessages;
            long received = (long) MessageEventList.numberOfReceivedMessages;
            long lost = sent - received;
            String note = "CupCarbon Klaines 8.2 ZigBee star topology simulation";

            csvContent.append(n).append(",")
                      .append((int)simTime).append(",")
                      .append(sent).append(",")
                      .append(received).append(",")
                      .append(lost).append(",")
                      .append(note).append("\n");

            System.out.printf("  N=%2d: sim_time=%ds, sent=%d, received=%d, lost=%d\n",
                    n, (int)simTime, sent, received, lost);
        }

        try (PrintWriter pw = new PrintWriter(new FileWriter(csvFile))) {
            pw.print(csvContent.toString());
        }
        System.out.println("Saved results to: " + csvFile.getAbsolutePath());
        System.exit(0);
    }
}
