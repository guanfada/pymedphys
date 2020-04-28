/// <reference types="cypress" />

describe("When using a Patient ID of 989898 and selecting the first iCOM record", () => {
  before(() => {
    cy.start()

    cy.get(".stTextInput input")
      .first()
      .type("989898{enter}");

    cy.compute()

    cy.get(".stMultiSelect")
      .first()
      .type("2020-04-29 07:47:29{enter}")

    cy.compute()
  });

  it("should have 4 fields that read Total MU: 150.0", () => {
    cy.textMatch('Total MU', 4, '150.0')
  });

  it("should have 3 fields that read Patient Name: PHYSICS, Mock", () => {
    cy.textMatch('Patient Name', 3, 'PHYSICS, Mock')
  });
});