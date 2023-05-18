plugins {
    application
    `java-library`
    id("com.github.johnrengelman.shadow") version "7.1.2"
}

val edcGroupId: String by project
val edcVersion: String by project

dependencies {
    testImplementation("org.junit.jupiter:junit-jupiter:5.9.1")
    implementation("$edcGroupId:configuration-filesystem:$edcVersion")
    implementation("$edcGroupId:control-plane-core:$edcVersion")
    implementation("$edcGroupId:api-observability:$edcVersion")
    implementation("$edcGroupId:iam-mock:$edcVersion")
    implementation("$edcGroupId:auth-tokenbased:$edcVersion")
    implementation("$edcGroupId:management-api:$edcVersion")
    implementation("$edcGroupId:ids:$edcVersion")
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
}

application {
    mainClass.set("org.eclipse.edc.boot.system.runtime.BaseRuntime")
}

tasks.withType<com.github.jengelman.gradle.plugins.shadow.tasks.ShadowJar> {
    exclude("**/pom.properties", "**/pom.xm")
    mergeServiceFiles()
    archiveFileName.set("consumer.jar")
}
