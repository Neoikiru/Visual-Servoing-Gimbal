/**
 * @file stepper_control.ino
 * @brief Non-blocking serial slave driver for stepper control.
 *
 * Receives discrete relative step commands (<X,Y>) from a Python PD controller
 * via USB serial at 115200 baud. Implements hardware E-STOP lockouts and uses
 * AccelStepper for smooth, jerk-free motion profiles.
 */

#include <AccelStepper.h>

// PIN DEFINITIONS
#define enPin 8                 // Stepper driver Enable pin (LOW to enable)
#define stepXPin 2              // Step pin for X-axis (Yaw) stepper
#define dirXPin 5               // Direction pin for X-axis (Yaw) stepper
#define stepYPin 3              // Step pin for Y-axis (Pitch) stepper
#define dirYPin 6               // Direction pin for Y-axis (Pitch) stepper

AccelStepper stepperY(AccelStepper::DRIVER, stepYPin, dirYPin); // Pitch stepper
AccelStepper stepperX(AccelStepper::DRIVER, stepXPin, dirXPin); // Yaw stepper

// SERIAL BUFFER SETUP
const byte numChars = 32;
char receivedChars[numChars];
boolean newData = false;

// Hardware State Flag
boolean isArmed = true;         // True = normal operation, False = E-STOP locked

// SETUP FUNCTION
void setup() {
    // Initialize serial link
    Serial.begin(115200);
    while (!Serial);

    // Initialize Driver
    pinMode(enPin, OUTPUT);
    digitalWrite(enPin, LOW); // Engage motor

    // Configure Stepper Kinematics
    stepperX.setMaxSpeed(5000.0);
    stepperX.setAcceleration(8000.0);
    
    stepperY.setMaxSpeed(5000.0);
    stepperY.setAcceleration(8000.0);

    // Zero internal tracking
    stepperX.setCurrentPosition(0);
    stepperY.setCurrentPosition(0);

    Serial.println(F("[FIRMWARE] Slave Driver Online."));
}

// MAIN LOOP
void loop() {
    // Catch serial bytes
    recvWithEndMarker();

    // Process payload
    if (newData) {
        parseData();
        newData = false;
    }

    // Run motors
    if (isArmed) {
        stepperX.run();
        stepperY.run();
    }
}

// SERIAL RECEIVER
void recvWithEndMarker() {
    static byte ndx = 0;
    char endMarker = '\n';
    char rc;

    // Pull bytes
    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        if (rc != endMarker) {
            receivedChars[ndx] = rc;
            ndx++;
            if (ndx >= numChars) {
                ndx = numChars - 1; // Prevent buffer
            }
        } else {
            receivedChars[ndx] = '\0'; // Terminate the string
            ndx = 0;
            newData = true;
        }
    }
}

// PAYLOAD PARSER
void parseData() {
    // Catch Commands
    if (strcmp(receivedChars, "<STOP>") == 0) {
        executeEmergencyStop();
        return;
    }
    if (strcmp(receivedChars, "<ARM>") == 0) {
        armSystem();
        return;
    }
    if (strcmp(receivedChars, "<HOME>") == 0) {
        returnToAbsoluteHome();
        return;
    }
    if (strcmp(receivedChars, "<ZERO>") == 0) {
        setCurrentAsAbsoluteHome();
        return;
    }

    // Parse Steps: <stepsX,stepsY>
    if (receivedChars[0] == '<' && isArmed) {
        char *strtokIndx;

        strtokIndx = strtok(receivedChars + 1, ",");
        if (strtokIndx != NULL) {
            long stepsX = atol(strtokIndx); // Convert ASCII to long integer

            strtokIndx = strtok(NULL, ">");
            if (strtokIndx != NULL) {
                long stepsY = atol(strtokIndx);

                // Command offsets
                stepperX.move(stepsX);
                stepperY.move(stepsY);
            }
        }
    }
}

// HOMING HANDLERS
void returnToAbsoluteHome() {
    if (!isArmed) return;
    
    Serial.println(F("[FIRMWARE] Returning to (0,0)."));
    
    stepperX.moveTo(0);
    stepperY.moveTo(0);
}

void setCurrentAsAbsoluteHome() {
    if (!isArmed) return;

    stepperX.setCurrentPosition(0);
    stepperY.setCurrentPosition(0);
    
    Serial.println(F("[FIRMWARE] Position locked as (0,0)."));
}

// SAFETY STATE HANDLERS
void executeEmergencyStop() {
    isArmed = false;

    stepperX.stop();
    stepperY.stop();

    // Disengage coils
    digitalWrite(enPin, HIGH);

    Serial.println(F("[FIRMWARE] Coils disengaged."));
}

void armSystem() {
    isArmed = true;
    
    // Re-engage motors
    digitalWrite(enPin, LOW);

    stepperX.setCurrentPosition(stepperX.currentPosition());
    stepperY.setCurrentPosition(stepperY.currentPosition());

    Serial.println(F("[FIRMWARE] Coils active."));
}